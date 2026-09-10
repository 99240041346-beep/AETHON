package ai.aethon.android;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;

public final class MainActivity extends Activity implements TextToSpeech.OnInitListener {
    private static final int REQUEST_RECORD_AUDIO = 7001;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView status;
    private EditText apiUrl;
    private EditText transcript;
    private SpeechRecognizer speechRecognizer;
    private TextToSpeech textToSpeech;
    private boolean ttsReady;
    private String sessionId;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState); buildUi(); textToSpeech = new TextToSpeech(this, this);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO);
        else initSpeechRecognizer();
    }
    private void buildUi() {
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(32,48,32,32); root.setGravity(Gravity.CENTER_HORIZONTAL);
        TextView title=new TextView(this); title.setText("AETHON"); title.setTextSize(32); title.setGravity(Gravity.CENTER); root.addView(title,new LinearLayout.LayoutParams(-1,-2));
        TextView subtitle=new TextView(this); subtitle.setText("Think. Create. Act.\nTelugu AI Assistant"); subtitle.setTextSize(16); subtitle.setGravity(Gravity.CENTER); root.addView(subtitle,new LinearLayout.LayoutParams(-1,-2));
        apiUrl=new EditText(this); apiUrl.setHint("AETHON API URL"); apiUrl.setSingleLine(true); apiUrl.setText("http://10.0.2.2:8000"); root.addView(apiUrl,new LinearLayout.LayoutParams(-1,-2));
        Button health=new Button(this); health.setText("Check AETHON API"); health.setOnClickListener(v->checkHealth()); root.addView(health,new LinearLayout.LayoutParams(-1,-2));
        Button listen=new Button(this); listen.setText("🎙 Hey Buddy / మాట్లాడండి"); listen.setOnClickListener(v->startListening()); root.addView(listen,new LinearLayout.LayoutParams(-1,-2));
        transcript=new EditText(this); transcript.setHint("మీ command / Your command"); transcript.setMinLines(3); transcript.setGravity(Gravity.TOP|Gravity.START); root.addView(transcript,new LinearLayout.LayoutParams(-1,-2));
        Button send=new Button(this); send.setText("➤ Ask AETHON"); send.setOnClickListener(v->sendToAethon()); root.addView(send,new LinearLayout.LayoutParams(-1,-2));
        Button speak=new Button(this); speak.setText("🔊 AETHON Voice"); speak.setOnClickListener(v->speakText(transcript.getText().toString().trim())); root.addView(speak,new LinearLayout.LayoutParams(-1,-2));
        TextView device=new TextView(this); device.setText(deviceInfo()); device.setTextSize(15); device.setPadding(0,24,0,16); root.addView(device,new LinearLayout.LayoutParams(-1,-2));
        status=new TextView(this); status.setText("Status: ready\nSay: Hey Buddy"); status.setTextSize(15); root.addView(status,new LinearLayout.LayoutParams(-1,-2));
        ScrollView scroll=new ScrollView(this); scroll.addView(root); setContentView(scroll);
    }
    private String deviceInfo(){return "Device\nManufacturer: "+Build.MANUFACTURER+"\nModel: "+Build.MODEL+"\nAndroid: "+Build.VERSION.RELEASE+" (API "+Build.VERSION.SDK_INT+")";}
    private void initSpeechRecognizer(){
        if(!SpeechRecognizer.isRecognitionAvailable(this)){status.setText("Status: speech recognition unavailable");return;}
        speechRecognizer=SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(new RecognitionListener(){
            @Override public void onReadyForSpeech(Bundle p){status.setText("Status: listening… Telugu speech is active");}
            @Override public void onBeginningOfSpeech(){}
            @Override public void onRmsChanged(float r){}
            @Override public void onBufferReceived(byte[] b){}
            @Override public void onEndOfSpeech(){status.setText("Status: processing speech…");}
            @Override public void onError(int e){status.setText("Status: speech error "+e+" — tap Speak again");}
            @Override public void onResults(Bundle r){ArrayList<String> m=r.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);if(m!=null&&!m.isEmpty()){transcript.setText(m.get(0));transcript.setSelection(transcript.length());status.setText("Status: heard your request — sending to AETHON");sendToAethon();}else status.setText("Status: no speech recognized");}
            @Override public void onPartialResults(Bundle p){}
            @Override public void onEvent(int e,Bundle p){}
        });
    }
    private void startListening(){if(speechRecognizer==null)initSpeechRecognizer();if(speechRecognizer==null)return;Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false);i.putExtra(RecognizerIntent.EXTRA_PROMPT,"AETHON వింటోంది…");speechRecognizer.startListening(i);}
    @Override public void onInit(int code){if(code!=TextToSpeech.SUCCESS){status.setText("Status: AETHON voice engine unavailable");return;}int result=textToSpeech.setLanguage(new Locale("te","IN"));if(result==TextToSpeech.LANG_MISSING_DATA||result==TextToSpeech.LANG_NOT_SUPPORTED){result=textToSpeech.setLanguage(Locale.ENGLISH);ttsReady=result!=TextToSpeech.LANG_MISSING_DATA&&result!=TextToSpeech.LANG_NOT_SUPPORTED;status.setText(ttsReady?"Status: voice ready (English fallback)":"Status: no supported TTS voice installed");}else{ttsReady=true;textToSpeech.setSpeechRate(.88f);textToSpeech.setPitch(.82f);status.setText("Status: AETHON Telugu voice ready");}}
    private void speakText(String text){if(!ttsReady){status.setText("Status: voice engine is not ready yet");return;}if(text.isEmpty())text="నమస్కారం Harsha. నేను AETHON. చెప్పు.";textToSpeech.speak(text,TextToSpeech.QUEUE_FLUSH,null,"aethon-response");status.setText("Status: AETHON is speaking…");}
    private void sendToAethon(){
        final String text=transcript.getText().toString().trim();if(text.isEmpty()){status.setText("Status: speak or type a request first");return;}
        final String base=apiUrl.getText().toString().trim().replaceAll("/+$","");status.setText("Status: AETHON is thinking…");
        new Thread(()->{HttpURLConnection c=null;try{
            URL u=new URL(base+"/v1/voice/respond");c=(HttpURLConnection)u.openConnection();c.setRequestMethod("POST");c.setDoOutput(true);c.setConnectTimeout(8000);c.setReadTimeout(30000);c.setRequestProperty("Content-Type","application/json; charset=UTF-8");
            String safe=escapeJson(text);String sid=sessionId==null?"":escapeJson(sessionId);String body="{\"transcript\":\""+safe+"\",\"language\":\"te-IN\""+(sid.isEmpty()?"":",\"session_id\":\""+sid+"\"")+"}";
            try(OutputStream out=c.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}
            int code=c.getResponseCode();BufferedReader rd=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=rd.readLine())!=null)b.append(line);String json=b.toString();if(code>=400)throw new IllegalStateException("HTTP "+code+": "+json);
            String answer=extractJson(json,"response");String newSession=extractJson(json,"session_id");String action=extractJson(json,"action");String actionPackage=extractJson(json,"action_package");if(!newSession.isEmpty())sessionId=newSession;
            final String a=answer,act=action,pkg=actionPackage;handler.post(()->{status.setText("Status: AETHON response received (HTTP "+code+")");speakText(a);if("android.open_app".equals(act)&&!pkg.isEmpty())launchAllowedApp(pkg);});
        }catch(Exception e){handler.post(()->status.setText("Status: AETHON connection failed — "+e.getMessage()));}finally{if(c!=null)c.disconnect();}}).start();
    }
    private static String escapeJson(String v){return v.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r");}
    private String extractJson(String json,String key){String marker="\""+key+"\":\"";int start=json.indexOf(marker);if(start<0)return"";start+=marker.length();StringBuilder out=new StringBuilder();boolean escaped=false;for(int i=start;i<json.length();i++){char ch=json.charAt(i);if(escaped){out.append(ch);escaped=false;}else if(ch=='\\')escaped=true;else if(ch=='"')break;else out.append(ch);}return out.toString().replace("\\n","\n").replace("\\\"","\"").replace("\\\\","\\");}
    private void launchAllowedApp(String packageName){if(!isAllowedPackage(packageName)){status.setText("Status: blocked unallowlisted Android package");return;}try{Intent launch=getPackageManager().getLaunchIntentForPackage(packageName);if(launch==null){status.setText("Status: requested app is not installed");return;}launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(launch);status.setText("Status: AETHON opened the authorized app");}catch(Exception e){status.setText("Status: app launch failed — "+e.getMessage());}}
    private boolean isAllowedPackage(String p){return "com.google.android.youtube".equals(p)||"com.android.chrome".equals(p)||"com.google.android.calculator".equals(p)||"com.android.settings".equals(p);}
    private void checkHealth(){final String base=apiUrl.getText().toString().trim().replaceAll("/+$","");status.setText("Status: checking…");new Thread(()->{HttpURLConnection c=null;try{URL u=new URL(base+"/health");c=(HttpURLConnection)u.openConnection();c.setRequestMethod("GET");c.setConnectTimeout(5000);c.setReadTimeout(5000);int code=c.getResponseCode();BufferedReader rd=new BufferedReader(new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=rd.readLine())!=null)b.append(line);final String result=b.toString();handler.post(()->status.setText("Status: API reachable\nHTTP "+code+"\n"+result));}catch(Exception e){handler.post(()->status.setText("Status: connection failed\n"+e.getClass().getSimpleName()+": "+e.getMessage()));}finally{if(c!=null)c.disconnect();}}).start();}
    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==REQUEST_RECORD_AUDIO){if(g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED){initSpeechRecognizer();status.setText("Status: microphone permission granted; voice ready");}else status.setText("Status: microphone permission denied; voice input disabled");}}
    @Override protected void onDestroy(){if(speechRecognizer!=null){speechRecognizer.destroy();speechRecognizer=null;}if(textToSpeech!=null){textToSpeech.stop();textToSpeech.shutdown();textToSpeech=null;}super.onDestroy();}
}
