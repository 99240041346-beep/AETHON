package ai.aethon.android;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.view.Gravity;
import android.view.View;
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

    private int dp(float value) { return (int) (value * getResources().getDisplayMetrics().density + 0.5f); }
    private TextView label(String text, float size) {
        TextView v = new TextView(this); v.setText(text); v.setTextSize(size); v.setTextColor(Color.rgb(226,232,240));
        v.setPadding(0, dp(6), 0, dp(6)); return v;
    }
    private GradientDrawable cardBackground() {
        GradientDrawable g = new GradientDrawable(); g.setColor(Color.rgb(24,32,48)); g.setCornerRadius(dp(20)); g.setStroke(dp(1), Color.rgb(51,65,85)); return g;
    }
    private Button actionButton(String text) {
        Button b = new Button(this); b.setText(text); b.setTextSize(14); b.setAllCaps(false); b.setTextColor(Color.WHITE); b.setMinHeight(dp(48)); b.setPadding(dp(12),0,dp(12),0);
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, new int[]{Color.rgb(37,99,235),Color.rgb(124,58,237)}); g.setCornerRadius(dp(16)); b.setBackground(g); return b;
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState); buildUi(); textToSpeech = new TextToSpeech(this, this);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO); else initSpeechRecognizer();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(20),dp(28),dp(20),dp(28)); root.setBackgroundColor(Color.rgb(8,13,24));
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true); scroll.addView(root); setContentView(scroll);

        TextView brand = label("AETHON", 32); brand.setTextColor(Color.WHITE); brand.setTypeface(null, 1); brand.setGravity(Gravity.CENTER); root.addView(brand, new LinearLayout.LayoutParams(-1, -2));
        TextView tagline = label("Your intelligent Telugu AI companion", 15); tagline.setTextColor(Color.rgb(148,163,184)); tagline.setGravity(Gravity.CENTER); root.addView(tagline, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout statusCard = new LinearLayout(this); statusCard.setOrientation(LinearLayout.VERTICAL); statusCard.setPadding(dp(18),dp(14),dp(18),dp(14)); statusCard.setBackground(cardBackground()); LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1,-2); cp.setMargins(0,dp(22),0,dp(12)); root.addView(statusCard,cp);
        TextView live = label("●  AETHON READY", 13); live.setTextColor(Color.rgb(74,222,128)); statusCard.addView(live);
        status = label("Listening, thinking and acting securely", 14); status.setTextColor(Color.rgb(203,213,225)); statusCard.addView(status);

        LinearLayout chat = new LinearLayout(this); chat.setOrientation(LinearLayout.VERTICAL); chat.setPadding(dp(18),dp(16),dp(18),dp(16)); chat.setBackground(cardBackground()); LinearLayout.LayoutParams chatp=new LinearLayout.LayoutParams(-1,-2); chatp.setMargins(0,dp(4),0,dp(12)); root.addView(chat,chatp);
        TextView chatTitle=label("Conversation",18); chatTitle.setTypeface(null,1); chat.addView(chatTitle);
        transcript=new EditText(this); transcript.setHint("నాకు ఏమి చేయాలో చెప్పండి…  /  Tell AETHON what to do"); transcript.setHintTextColor(Color.rgb(100,116,139)); transcript.setTextColor(Color.WHITE); transcript.setTextSize(16); transcript.setGravity(Gravity.TOP|Gravity.START); transcript.setMinLines(4); transcript.setPadding(dp(14),dp(12),dp(14),dp(12)); GradientDrawable inputBg=new GradientDrawable(); inputBg.setColor(Color.rgb(15,23,42)); inputBg.setCornerRadius(dp(14)); inputBg.setStroke(dp(1),Color.rgb(51,65,85)); transcript.setBackground(inputBg); chat.addView(transcript,new LinearLayout.LayoutParams(-1,dp(120)));

        LinearLayout row1=new LinearLayout(this); row1.setOrientation(LinearLayout.HORIZONTAL); row1.setGravity(Gravity.CENTER); row1.setPadding(0,dp(12),0,0); chat.addView(row1,new LinearLayout.LayoutParams(-1,-2));
        Button listen=actionButton("🎙  Hey Buddy"); listen.setOnClickListener(v->startListening()); row1.addView(listen,new LinearLayout.LayoutParams(0,dp(50),1));
        Button send=actionButton("➤  Ask AETHON"); send.setOnClickListener(v->sendToAethon()); LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(0,dp(50),1);sp.setMargins(dp(8),0,0,0);row1.addView(send,sp);
        Button speak=actionButton("🔊  Speak"); speak.setOnClickListener(v->speakText(transcript.getText().toString().trim())); LinearLayout.LayoutParams vp=new LinearLayout.LayoutParams(-1,dp(48));vp.setMargins(0,dp(8),0,0);chat.addView(speak,vp);

        LinearLayout connection=new LinearLayout(this); connection.setOrientation(LinearLayout.VERTICAL); connection.setPadding(dp(18),dp(14),dp(18),dp(14)); connection.setBackground(cardBackground()); LinearLayout.LayoutParams conp=new LinearLayout.LayoutParams(-1,-2);conp.setMargins(0,dp(4),0,dp(12));root.addView(connection,conp);
        connection.addView(label("AETHON Cloud / Local API",16));
        apiUrl=new EditText(this); apiUrl.setHint("API URL");apiUrl.setText("http://10.0.2.2:8000");apiUrl.setSingleLine(true);apiUrl.setTextColor(Color.WHITE);apiUrl.setHintTextColor(Color.rgb(100,116,139));connection.addView(apiUrl,new LinearLayout.LayoutParams(-1,dp(52)));
        Button health=actionButton("✓  Check API Connection");health.setOnClickListener(v->checkHealth());LinearLayout.LayoutParams hp=new LinearLayout.LayoutParams(-1,dp(48));hp.setMargins(0,dp(8),0,0);connection.addView(health,hp);

        LinearLayout device=new LinearLayout(this);device.setOrientation(LinearLayout.VERTICAL);device.setPadding(dp(18),dp(14),dp(18),dp(14));device.setBackground(cardBackground());root.addView(device,new LinearLayout.LayoutParams(-1,-2));
        device.addView(label("Device",16)); TextView info=label(deviceInfo(),14);info.setTextColor(Color.rgb(148,163,184));device.addView(info);
        TextView security=label("🔒  Safety Kernel active  •  Android actions are allowlisted",12);security.setTextColor(Color.rgb(96,165,250));security.setPadding(0,dp(12),0,0);device.addView(security);
    }

    private String deviceInfo(){return "Manufacturer: "+Build.MANUFACTURER+"\nModel: "+Build.MODEL+"\nAndroid: "+Build.VERSION.RELEASE+" (API "+Build.VERSION.SDK_INT+")";}
    private void initSpeechRecognizer(){if(!SpeechRecognizer.isRecognitionAvailable(this)){status.setText("Speech recognition unavailable");return;}speechRecognizer=SpeechRecognizer.createSpeechRecognizer(this);speechRecognizer.setRecognitionListener(new RecognitionListener(){
        @Override public void onReadyForSpeech(Bundle p){status.setText("Listening… Telugu speech is active");}
        @Override public void onBeginningOfSpeech(){}
        @Override public void onRmsChanged(float r){}
        @Override public void onBufferReceived(byte[] b){}
        @Override public void onEndOfSpeech(){status.setText("Processing your command…");}
        @Override public void onError(int e){status.setText("Speech error "+e+" — tap Hey Buddy again");}
        @Override public void onResults(Bundle r){ArrayList<String> m=r.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);if(m!=null&&!m.isEmpty()){transcript.setText(m.get(0));transcript.setSelection(transcript.length());status.setText("Request received — AETHON is thinking…");sendToAethon();}else status.setText("No speech recognized");}
        @Override public void onPartialResults(Bundle p){} @Override public void onEvent(int e,Bundle p){}
    });}
    private void startListening(){if(speechRecognizer==null)initSpeechRecognizer();if(speechRecognizer==null)return;Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false);i.putExtra(RecognizerIntent.EXTRA_PROMPT,"AETHON వింటోంది…");speechRecognizer.startListening(i);}
    @Override public void onInit(int code){if(code!=TextToSpeech.SUCCESS){status.setText("AETHON voice engine unavailable");return;}int result=textToSpeech.setLanguage(new Locale("te","IN"));if(result==TextToSpeech.LANG_MISSING_DATA||result==TextToSpeech.LANG_NOT_SUPPORTED){result=textToSpeech.setLanguage(Locale.ENGLISH);ttsReady=result!=TextToSpeech.LANG_MISSING_DATA&&result!=TextToSpeech.LANG_NOT_SUPPORTED;status.setText(ttsReady?"Voice ready (English fallback)":"No supported TTS voice installed");}else{ttsReady=true;textToSpeech.setSpeechRate(.88f);textToSpeech.setPitch(.82f);status.setText("AETHON Telugu voice ready");}}
    private void speakText(String text){if(!ttsReady){status.setText("Voice engine is not ready");return;}if(text.isEmpty())text="నమస్కారం Harsha. నేను AETHON. చెప్పండి.";textToSpeech.speak(text,TextToSpeech.QUEUE_FLUSH,null,"aethon-response");status.setText("AETHON is speaking…");}
    private void sendToAethon(){final String text=transcript.getText().toString().trim();if(text.isEmpty()){status.setText("Type or speak a request first");return;}final String base=apiUrl.getText().toString().trim().replaceAll("/+$","");status.setText("AETHON is thinking…");new Thread(()->{HttpURLConnection c=null;try{URL u=new URL(base+"/v1/voice/respond");c=(HttpURLConnection)u.openConnection();c.setRequestMethod("POST");c.setDoOutput(true);c.setConnectTimeout(8000);c.setReadTimeout(30000);c.setRequestProperty("Content-Type","application/json; charset=UTF-8");String safe=escapeJson(text);String sid=sessionId==null?"":escapeJson(sessionId);String body="{\"transcript\":\""+safe+"\",\"language\":\"te-IN\""+(sid.isEmpty()?"":",\"session_id\":\""+sid+"\"")+"}";try(OutputStream out=c.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}int code=c.getResponseCode();BufferedReader rd=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=rd.readLine())!=null)b.append(line);String json=b.toString();if(code>=400)throw new IllegalStateException("HTTP "+code+": "+json);String answer=extractJson(json,"response");String newSession=extractJson(json,"session_id");String action=extractJson(json,"action");String actionPackage=extractJson(json,"action_package");if(!newSession.isEmpty())sessionId=newSession;final String a=answer,act=action,pkg=actionPackage;handler.post(()->{status.setText("AETHON replied • HTTP "+code);speakText(a);if("android.open_app".equals(act)&&!pkg.isEmpty())launchAllowedApp(pkg);});}catch(Exception e){handler.post(()->status.setText("Connection failed — "+e.getMessage()));}finally{if(c!=null)c.disconnect();}}).start();}
    private static String escapeJson(String v){return v.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r");}
    private String extractJson(String json,String key){String marker="\""+key+"\":\"";int start=json.indexOf(marker);if(start<0)return"";start+=marker.length();StringBuilder out=new StringBuilder();boolean escaped=false;for(int i=start;i<json.length();i++){char ch=json.charAt(i);if(escaped){out.append(ch);escaped=false;}else if(ch=='\\')escaped=true;else if(ch=='"')break;else out.append(ch);}return out.toString().replace("\\n","\n").replace("\\\"","\"").replace("\\\\","\\");}
    private void launchAllowedApp(String packageName){if(!isAllowedPackage(packageName)){status.setText("Blocked: unallowlisted Android package");return;}try{Intent launch=getPackageManager().getLaunchIntentForPackage(packageName);if(launch==null){status.setText("Requested app is not installed");return;}launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(launch);status.setText("Authorized app opened successfully");}catch(Exception e){status.setText("App launch failed — "+e.getMessage());}}
    private boolean isAllowedPackage(String p){return "com.google.android.youtube".equals(p)||"com.android.chrome".equals(p)||"com.google.android.calculator".equals(p)||"com.android.settings".equals(p);}
    private void checkHealth(){final String base=apiUrl.getText().toString().trim().replaceAll("/+$","");status.setText("Checking AETHON API…");new Thread(()->{HttpURLConnection c=null;try{URL u=new URL(base+"/health");c=(HttpURLConnection)u.openConnection();c.setRequestMethod("GET");c.setConnectTimeout(5000);c.setReadTimeout(5000);int code=c.getResponseCode();BufferedReader rd=new BufferedReader(new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=rd.readLine())!=null)b.append(line);final String result=b.toString();handler.post(()->status.setText("API connected • HTTP "+code+"\n"+result));}catch(Exception e){handler.post(()->status.setText("API connection failed\n"+e.getClass().getSimpleName()+": "+e.getMessage()));}finally{if(c!=null)c.disconnect();}}).start();}
    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==REQUEST_RECORD_AUDIO){if(g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED){initSpeechRecognizer();status.setText("Microphone ready — tap Hey Buddy");}else status.setText("Microphone permission denied");}}
    @Override protected void onDestroy(){if(speechRecognizer!=null){speechRecognizer.destroy();speechRecognizer=null;}if(textToSpeech!=null){textToSpeech.stop();textToSpeech.shutdown();textToSpeech=null;}super.onDestroy();}
}
