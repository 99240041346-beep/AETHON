from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aethon.postgres import PostgresStore

class CommandTransportError(ValueError): pass

@dataclass(frozen=True)
class PersistedCommand:
    command_id: str
    owner_id: str
    device_id: str
    capability: str
    arguments: dict[str, Any]
    nonce: str
    issued_at: float
    expires_at: float
    status: str

class AndroidCommandTransport:
    MAX_TTL_SECONDS=30
    WORKFLOW_STATES={"RUNNING","PAUSED","CANCELLED","COMPLETED","FAILED"}
    MAX_WORKFLOW_STEP_RETRIES=2
    def __init__(self,database_url:str|None=None): self.store=PostgresStore(database_url)
    @staticmethod
    def _ts(value:float)->datetime:return datetime.fromtimestamp(value,tz=timezone.utc)
    def enqueue(self,*,owner_id:str,device_id:str,capability:str,arguments:dict[str,Any],nonce:str,approved:bool,ttl_seconds:float=15)->PersistedCommand:
        if not owner_id or not device_id or not capability or not nonce: raise CommandTransportError("owner, device, capability and nonce are required")
        if ttl_seconds<=0 or ttl_seconds>self.MAX_TTL_SECONDS: raise CommandTransportError("invalid command TTL")
        command_id=str(uuid4());issued=time.time();expires=issued+ttl_seconds
        try:self.store.execute("""INSERT INTO device_commands (command_id, owner_id, device_id, capability, arguments_json, nonce, status, verified, issued_at, expires_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s,'ACCEPTED',FALSE,%s,%s)""",(command_id,owner_id,device_id,capability,json.dumps({**arguments,"_approved":approved}),nonce,self._ts(issued),self._ts(expires)))
        except Exception as exc: raise CommandTransportError("command could not be persisted") from exc
        return PersistedCommand(command_id,owner_id,device_id,capability,arguments,nonce,issued,expires,"ACCEPTED")
    def claim_next(self,*,device_id:str,owner_id:str)->PersistedCommand|None:
        now=self._ts(time.time())
        query="""WITH next_command AS (SELECT command_id FROM device_commands WHERE device_id=%s AND owner_id=%s AND status='ACCEPTED' AND expires_at>%s AND claimed_at IS NULL AND COALESCE(arguments_json->'_workflow'->>'state','RUNNING')='RUNNING' ORDER BY issued_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED) UPDATE device_commands AS dc SET claimed_at=NOW() FROM next_command WHERE dc.command_id=next_command.command_id RETURNING dc.command_id,dc.owner_id,dc.device_id,dc.capability,dc.arguments_json,dc.nonce,dc.issued_at,dc.expires_at,dc.status"""
        rows=self.store.execute(query,(device_id,owner_id,now))
        if not rows:
            expired=self.expire_pending(device_id=device_id,owner_id=owner_id)
            if expired: self.recover_expired_workflow(device_id=device_id,owner_id=owner_id)
            rows=self.store.execute(query,(device_id,owner_id,self._ts(time.time())))
            if not rows:return None
        r=rows[0];args=r[4] if isinstance(r[4],dict) else json.loads(r[4]);args.pop("_approved",None)
        return PersistedCommand(str(r[0]),r[1],r[2],r[3],args,r[5],r[6].timestamp(),r[7].timestamp(),r[8])
    def expire_pending(self,*,device_id:str,owner_id:str)->int:return len(self.store.execute("UPDATE device_commands SET status='EXPIRED' WHERE device_id=%s AND owner_id=%s AND status='ACCEPTED' AND expires_at<=NOW() RETURNING command_id",(device_id,owner_id)))
    def recover_expired_workflow(self,*,device_id:str,owner_id:str)->PersistedCommand|None:
        rows=self.store.execute("""SELECT command_id,capability,arguments_json FROM device_commands WHERE device_id=%s AND owner_id=%s AND status='EXPIRED' AND arguments_json->'_workflow'->>'id' IS NOT NULL ORDER BY completed_at DESC NULLS LAST, issued_at DESC LIMIT 1""",(device_id,owner_id))
        if not rows:return None
        command_id,capability,raw_args=rows[0];args=raw_args if isinstance(raw_args,dict) else json.loads(raw_args or "{}");workflow=args.get("_workflow") if isinstance(args.get("_workflow"),dict) else None
        if not workflow or workflow.get("state","RUNNING")!="RUNNING":return None
        next_index=workflow.get("next_index");steps=workflow.get("steps",[])
        if not isinstance(next_index,int) or not isinstance(steps,list) or not (1<=next_index<=len(steps)):return None
        step_index=next_index-1;attempts=workflow.get("attempts",{});raw_attempt=attempts.get(str(step_index),0) if isinstance(attempts,dict) else 0
        try:attempt=max(0,int(raw_attempt))
        except (TypeError,ValueError):attempt=0
        if attempt>=self.MAX_WORKFLOW_STEP_RETRIES:self.set_workflow_state(workflow_id=str(workflow["id"]),owner_id=owner_id,state="FAILED");return None
        step=steps[step_index]
        if not isinstance(step,dict):return None
        existing=self.workflow_step_pending(workflow_id=str(workflow["id"]),owner_id=owner_id,step_index=step_index)
        if existing:
            found=self.get(command_id=existing["command_id"],owner_id=owner_id)
            if found:return PersistedCommand(found["command_id"],owner_id,device_id,found["capability"],found["arguments"],"",time.time(),time.time()+15,found["status"])
        retry_workflow={**workflow,"attempts":{**(attempts if isinstance(attempts,dict) else {}),str(step_index):attempt+1}}
        return self.enqueue_workflow_step(owner_id=owner_id,device_id=device_id,capability=capability,arguments=step.get("arguments",{}),workflow=retry_workflow,ttl_seconds=15)
    def cancel(self,*,command_id:str,owner_id:str)->bool:return bool(self.store.execute("UPDATE device_commands SET status='CANCELLED', completed_at=NOW(), error='cancelled by owner' WHERE command_id=%s AND owner_id=%s AND status='ACCEPTED' AND claimed_at IS NULL RETURNING command_id",(command_id,owner_id)))
    def record_result(self,*,command_id:str,device_id:str,owner_id:str,success:bool,verified:bool,result:dict[str,Any]|None=None,verification:dict[str,Any]|None=None,error:str|None=None)->dict[str,Any]:
        status='COMPLETED' if success and verified else 'REJECTED';rows=self.store.execute("""UPDATE device_commands SET status=%s, verified=%s, result_json=%s::jsonb, verification_json=%s::jsonb, error=%s, completed_at=NOW(), result_received_at=NOW() WHERE command_id=%s AND owner_id=%s AND device_id=%s AND status='ACCEPTED' AND claimed_at IS NOT NULL AND expires_at>NOW() RETURNING command_id,status,verified,error""",(status,verified,json.dumps(result or {}),json.dumps(verification or {}),error,command_id,owner_id,device_id))
        if not rows:raise CommandTransportError("command is missing, expired, cancelled, unclaimed, or already completed")
        r=rows[0];return {"command_id":str(r[0]),"status":r[1],"verified":bool(r[2]),"error":r[3]}
    def get(self,*,command_id:str,owner_id:str)->dict[str,Any]|None:
        rows=self.store.execute("SELECT command_id,owner_id,device_id,capability,status,verified,error,issued_at,expires_at,claimed_at,completed_at,arguments_json,result_json,verification_json FROM device_commands WHERE command_id=%s AND owner_id=%s",(command_id,owner_id))
        if not rows:return None
        r=rows[0];arguments=r[11] if isinstance(r[11],dict) else (json.loads(r[11]) if r[11] else {});arguments.pop("_approved",None)
        return {"command_id":str(r[0]),"owner_id":r[1],"device_id":r[2],"capability":r[3],"status":r[4],"verified":bool(r[5]),"error":r[6],"issued_at":r[7].isoformat(),"expires_at":r[8].isoformat(),"claimed_at":r[9].isoformat() if r[9] else None,"completed_at":r[10].isoformat() if r[10] else None,"arguments":arguments,"result":r[12] if isinstance(r[12],dict) else (json.loads(r[12]) if r[12] else None),"verification":r[13] if isinstance(r[13],dict) else (json.loads(r[13]) if r[13] else None)}
    def _workflow_row(self,*,workflow_id:str,owner_id:str)->dict[str,Any]|None:
        rows=self.store.execute("SELECT command_id,owner_id,device_id,capability,status,arguments_json,issued_at FROM device_commands WHERE owner_id=%s AND arguments_json->'_workflow'->>'id'=%s ORDER BY issued_at DESC LIMIT 1",(owner_id,workflow_id))
        if not rows:return None
        r=rows[0];args=r[5] if isinstance(r[5],dict) else json.loads(r[5] or "{}");workflow=args.get("_workflow") if isinstance(args.get("_workflow"),dict) else None
        return {"command_id":str(r[0]),"owner_id":r[1],"device_id":r[2],"capability":r[3],"status":r[4],"workflow":workflow,"issued_at":r[6].isoformat()}
    def workflow(self,*,workflow_id:str,owner_id:str):return self._workflow_row(workflow_id=workflow_id,owner_id=owner_id)
    def workflow_step_pending(self,*,workflow_id:str,owner_id:str,step_index:int):
        if step_index<0:return None
        rows=self.store.execute("SELECT command_id,device_id,capability,status FROM device_commands WHERE owner_id=%s AND arguments_json->'_workflow'->>'id'=%s AND arguments_json->'_workflow'->>'next_index'=%s AND status='ACCEPTED' ORDER BY issued_at DESC LIMIT 1",(owner_id,workflow_id,str(step_index+1)))
        if not rows:return None
        r=rows[0];return {"command_id":str(r[0]),"device_id":r[1],"capability":r[2],"status":r[3]}
    def enqueue_workflow_step(self,*,owner_id:str,device_id:str,capability:str,arguments:dict[str,Any],workflow:dict[str,Any],ttl_seconds:float=15)->PersistedCommand:
        workflow_id=str(workflow.get("id",""));next_index=workflow.get("next_index")
        if not workflow_id or not isinstance(next_index,int) or next_index<=0:raise CommandTransportError("invalid workflow step metadata")
        step_index=next_index-1;pending=self.workflow_step_pending(workflow_id=workflow_id,owner_id=owner_id,step_index=step_index)
        if pending:
            existing=self.get(command_id=pending["command_id"],owner_id=owner_id)
            if existing:return PersistedCommand(existing["command_id"],owner_id,device_id,existing["capability"],existing["arguments"],"",time.time(),time.time()+ttl_seconds,existing["status"])
        try:return self.enqueue(owner_id=owner_id,device_id=device_id,capability=capability,arguments={**arguments,"_workflow":workflow},nonce=secrets.token_urlsafe(24),approved=True,ttl_seconds=ttl_seconds)
        except CommandTransportError as exc:
            pending=self.workflow_step_pending(workflow_id=workflow_id,owner_id=owner_id,step_index=step_index)
            if pending:
                existing=self.get(command_id=pending["command_id"],owner_id=owner_id)
                if existing:return PersistedCommand(existing["command_id"],owner_id,device_id,existing["capability"],existing["arguments"],"",time.time(),time.time()+ttl_seconds,existing["status"])
            raise exc
    def set_workflow_state(self,*,workflow_id:str,owner_id:str,state:str):
        expected="PAUSED" if state=="RUNNING" else None
        return self.transition_workflow_state(workflow_id=workflow_id,owner_id=owner_id,state=state,expected_state=expected)
    def transition_workflow_state(self,*,workflow_id:str,owner_id:str,state:str,expected_state:str|None):
        if state not in self.WORKFLOW_STATES or (expected_state is not None and expected_state not in self.WORKFLOW_STATES):raise CommandTransportError("invalid workflow state")
        where="owner_id=%s AND arguments_json->'_workflow'->>'id'=%s";params:[Any]=[owner_id,workflow_id]
        if expected_state is not None:where += " AND arguments_json->'_workflow'->>'state'=%s";params.append(expected_state)
        rows=self.store.execute(f"UPDATE device_commands SET arguments_json=jsonb_set(arguments_json,'{{_workflow,state}}',%s::jsonb) WHERE {where} RETURNING command_id",tuple([json.dumps(state),*params]))
        if not rows:return None if expected_state is not None else self._workflow_row(workflow_id=workflow_id,owner_id=owner_id)
        if state=="CANCELLED":self.store.execute("UPDATE device_commands SET status='CANCELLED',completed_at=NOW(),error='workflow cancelled by owner' WHERE owner_id=%s AND arguments_json->'_workflow'->>'id'=%s AND status='ACCEPTED' AND claimed_at IS NULL",(owner_id,workflow_id))
        return self._workflow_row(workflow_id=workflow_id,owner_id=owner_id)
