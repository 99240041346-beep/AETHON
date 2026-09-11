from __future__ import annotations

import os
import time
from typing import Any, Protocol

import httpx


class ModelProvider(Protocol):
    name: str
    def generate(self, prompt: str) -> str: ...
    def health(self) -> bool: ...


class DeterministicProvider:
    name = "deterministic"
    def generate(self, prompt: str) -> str: return f"AETHON received: {prompt}"
    def health(self) -> bool: return True


class OpenAIResponsesProvider:
    """OpenAI Responses API provider with bounded retries and optional web search."""
    name = "openai"
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 45.0, retries: int = 2, web_search: bool = False) -> None:
        self.base_url=base_url.rstrip("/"); self.model=model; self.api_key=api_key; self.timeout=timeout; self.retries=max(0,retries); self.web_search=web_search
    def _headers(self)->dict[str,str]: return {"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}
    def _request(self,payload:dict[str,Any])->httpx.Response:
        last_error:Exception|None=None
        for attempt in range(self.retries+1):
            try:return httpx.post(f"{self.base_url}/responses",headers=self._headers(),json=payload,timeout=self.timeout)
            except (httpx.TimeoutException,httpx.NetworkError) as exc:
                last_error=exc
                if attempt<self.retries: time.sleep(min(.25*(2**attempt),1.0))
        raise RuntimeError("model provider request failed after bounded retries") from last_error
    @staticmethod
    def _extract_text(data:dict[str,Any])->str:
        output_text=data.get("output_text")
        if isinstance(output_text,str) and output_text.strip(): return output_text.strip()
        chunks:list[str]=[]
        for item in data.get("output",[]):
            if not isinstance(item,dict): continue
            for content in item.get("content",[]):
                if isinstance(content,dict) and isinstance(content.get("text"),str): chunks.append(content["text"])
        text="\n".join(x for x in chunks if x.strip()).strip()
        if not text: raise RuntimeError("model provider returned no text output")
        return text
    def generate(self,prompt:str)->str:
        payload={"model":self.model,"input":prompt}
        if self.web_search: payload["tools"]=[{"type":"web_search_preview"}]
        response=self._request(payload)
        if response.status_code>=400: raise RuntimeError(f"model provider returned HTTP {response.status_code}")
        return self._extract_text(response.json())
    def health(self)->bool:
        try:return httpx.get(f"{self.base_url}/models/{self.model}",headers=self._headers(),timeout=5.0).is_success
        except (httpx.HTTPError,OSError): return False


class OpenAICompatibleProvider:
    name="openai-compatible"
    def __init__(self,base_url:str,model:str,api_key:str,timeout:float=30.0,retries:int=2): self.base_url=base_url.rstrip("/");self.model=model;self.api_key=api_key;self.timeout=timeout;self.retries=max(0,retries)
    def _request(self,prompt:str)->httpx.Response:
        last_error:Exception|None=None
        for attempt in range(self.retries+1):
            try:return httpx.post(f"{self.base_url}/chat/completions",headers={"Authorization":f"Bearer {self.api_key}"},json={"model":self.model,"messages":[{"role":"user","content":prompt}]},timeout=self.timeout)
            except (httpx.TimeoutException,httpx.NetworkError) as exc:
                last_error=exc
                if attempt<self.retries: time.sleep(min(.25*(2**attempt),1.0))
        raise RuntimeError("model provider request failed after bounded retries") from last_error
    def generate(self,prompt:str)->str:
        response=self._request(prompt)
        if response.status_code>=400: raise RuntimeError(f"model provider returned HTTP {response.status_code}")
        data=response.json()
        try:return data["choices"][0]["message"]["content"]
        except (KeyError,IndexError,TypeError) as exc: raise RuntimeError("model provider returned an invalid response") from exc
    def health(self)->bool:
        try:return httpx.get(f"{self.base_url}/models",headers={"Authorization":f"Bearer {self.api_key}"},timeout=5.0).is_success
        except (httpx.HTTPError,OSError): return False


class ModelRouter:
    def __init__(self,provider:ModelProvider|None=None): self.provider=provider or self._from_environment()
    @staticmethod
    def _from_environment()->ModelProvider:
        provider=os.getenv("AETHON_MODEL_PROVIDER","deterministic").lower()
        if provider=="deterministic": return DeterministicProvider()
        if provider=="openai":
            base_url=os.getenv("AETHON_MODEL_BASE_URL","https://api.openai.com/v1");model=os.getenv("AETHON_MODEL_NAME","gpt-5.6-luna");api_key=os.getenv("AETHON_MODEL_API_KEY","")
            if not api_key: raise RuntimeError("AETHON_MODEL_API_KEY is required when AETHON_MODEL_PROVIDER=openai")
            web_search=os.getenv("AETHON_WEB_SEARCH","false").strip().lower() in {"1","true","yes","on"}
            return OpenAIResponsesProvider(base_url,model,api_key,web_search=web_search)
        if provider=="openai-compatible":
            base_url=os.getenv("AETHON_MODEL_BASE_URL");model=os.getenv("AETHON_MODEL_NAME");api_key=os.getenv("AETHON_MODEL_API_KEY")
            if not all((base_url,model,api_key)): raise RuntimeError("AETHON_MODEL_BASE_URL, AETHON_MODEL_NAME and AETHON_MODEL_API_KEY are required")
            return OpenAICompatibleProvider(base_url,model,api_key)
        raise RuntimeError(f"unsupported model provider: {provider}")
    def generate(self,prompt:str)->str: return self.provider.generate(prompt)
    def health(self)->bool: return self.provider.health()
