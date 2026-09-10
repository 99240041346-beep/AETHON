package ai.aethon.android;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.text.InputType;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
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
    private final android.os.Handler handler = new android.os.Handler(android.os.Looper.getMainLooper());
    private TextView status;
    private EditText apiUrl;
    private EditText deviceIdInput;
    private EditText deviceTokenInput;
    private EditText transcript;
    private LinearLayout messages;
    private SpeechRecognizer speechRecognizer;
    private TextToSpeech textToSpeech;
    private boolean ttsReady;
    private String sessionId;
    private String responseLocale = "te-IN";
    private String lastAssistantText = "";

    private int dp(float v) { return (int)(v * getResources().getDisplayMetrics().density + .5f); }
    private TextView label(String text, float size) { TextView v=new TextView(this);v.setText(text);v.setTextSize(size);v.setTextColor(Color.rgb(226,232,240));v.setPadding(0,dp(5),0,dp(5));return v; }
    private GradientDrawable card() { GradientDrawable g=new GradientDrawable();g.setColor(Color.rgb(24,32,48));g.setCornerRadius(dp(20));g.setStroke(dp(1),Color.rgb(51,65,85));return g; }
    private Button button(String text) { Button b=new Button(this);b.setText(text);b.setTextSize(14);b.setAllCaps(false);b.setTextColor(Color.WHITE);b.setMinHeight(dp(48));GradientDrawable g=new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,new int[]{Color.rgb(37,99,235),Color.rgb(124,58,237)});g.setCornerRadius(dp(16));b.setBackground(g);return b; }

    @Override protected void onCreate(Bundle state) { super.onCreate(state); buildUi(); textToSpeech=new TextToSpeech(this,this); if(Build.VERSION.SDK_INT>=23&&checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},REQUEST_RECORD_AUDIO);else initSpeech(); }

    private void buildUi() {
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(20),dp(28),dp(20),dp(24));root.setBackgroundColor(Color.rgb(8,13,24));
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.addView(root);setContentView(scroll);
        TextView brand=label("AETHON",32);brand.setGravity(Gravity.CENTER);brand.setTypeface(null,1);root.addView(brand,new LinearLayout.LayoutParams(-1,-2));
        TextView sub=label("Your intelligent multilingual AI companion",15);sub.setGravity(Gravity.CENTER);sub.setTextColor(Color.rgb(148,163,184));root.addView(sub,new LinearLayout.LayoutParams(-1,-2));
        LinearLayout sc=new LinearLayout(this);sc.setOrientation(LinearLayout.VERTICAL);sc.setPadding(dp(18),dp(14),dp(18),dp(14));sc.setBackground(card());LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,-2);sp.setMargins(0,dp(20),0,dp(10));root.addView(sc,sp);
        TextView ready=label("●  AETHON READY",13);ready.setTextColor(Color.rgb(74,222,128));sc.addView(ready);status=label("Listening • Thinking • Acting securely",14);status.setTextColor(Color.rgb(203,213,225));sc.addView(status);
        LinearLayout cc=new LinearLayout(this);cc.setOrientation(LinearLayout.VERTICAL);cc.setPadding(dp(18),dp(14),dp(18),dp(14));cc.setBackground(card());LinearLayout.LayoutParams ccp=new LinearLayout.LayoutParams(-1,-2);ccp.setMargins(0,dp(4),0,dp(10));root.addView(cc,ccp);
        cc.addView(label("Conversation",18));messages=new LinearLayout(this);messages.setOrientation(LinearLayout.VERTICAL);cc.addView(messages,new LinearLayout.LayoutParams(-1,-2));
        transcript=new EditText(this);transcript.setHint("తెలుగు / English / हिन्दी / தமிழ்…");transcript.setHintTextColor(Color.rgb(100,116,139));transcript.setTextColor(Color.WHITE);transcript.setTextSize(16);transcript.setGravity(Gravity.TOP|Gravity.START);transcript.setMinLines(3);transcript.setPadding(dp(14),dp(12),dp(14),dp(12));GradientDrawable ib=new GradientDrawable();ib.setColor(Color.rgb(15,23,42));ib.setCornerRadius(dp(14));ib.setStroke(dp(1),Color.rgb(51,65,85));transcript.setBackground(ib);cc.addView(transcript,new LinearLayout.LayoutParams(-1,dp(105)));
        LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER);cc.addView(row,new LinearLayout.LayoutParams(-1,-2));Button listen=button("🎙  Hey Buddy");listen.setOnClickListener(v->startListening());row.addView(listen,new LinearLayout.LayoutParams(0,dp(50),1));Button ask=button("➤  Ask AETHON");ask.setOnClickListener(v->sendAssistant());LinearLayout.LayoutParams ap=new LinearLayout.LayoutParams(0,dp(50),1);ap.setMargins(dp(8),0,0,0);row.addView(ask,ap);
        Button speak=button("🔊  Speak last response");speak.setOnClickListener(v->speakText(lastAssistantText));LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,dp(48));bp.setMargins(0,dp(8),0,0);cc.addView(speak,bp);
        LinearLayout lang=new LinearLayout(this);lang.setOrientation(LinearLayout.HORIZONTAL);lang.setPadding(dp(14),dp(10),dp(14),dp(10));lang.setBackground(card());root.addView(lang,new LinearLayout.LayoutParams(-1,-2));lang.addView(label("Language: Auto • Telugu + English",14),new LinearLayout.LayoutParams(0,-2,1));Button health=button("✓ API");health.setOnClickListener(v->checkHealth());lang.addView(health,new LinearLayout.LayoutParams(dp(90),dp(46)));
        LinearLayout device= new LinearLayout(this);device.setOrientation(LinearLayout.VERTICAL);device.setPadding(dp(18),dp(14),dp(18),dp(14));device.setBackground(card());LinearLayout.LayoutParams dpv=new LinearLayout.LayoutParams(-1,-2);dpv.setMargins(0,dp(10),0,dp(10));root.addView(device,dpv);device.addView(label("Android Device Link",18));
        apiUrl=field("Cloud API URL",false);apiUrl.setText("http://10.0.2.2:8000");device.addView(apiUrl);
        deviceIdInput=field("Registered device ID",false);device.addView(deviceIdInput);
        deviceTokenInput=field("Device token (kept in memory)",true);device.addView(deviceTokenInput);
        LinearLayout drow=new LinearLayout(this);drow.setGravity(Gravity.CENTER);device.addView(drow,new LinearLayout.LayoutParams(-1,dp(50)));Button connect=button("Connect device");connect.setOnClickListener(v->connectDevice());drow.addView(connect,new LinearLayout.LayoutParams(0,dp(50),1));Button disconnect=button("Disconnect");disconnect.setOnClickListener(v->{AndroidCommandService.stop(this);status.setText("Device link disconnected");});LinearLayout.LayoutParams dd=new LinearLayout.LayoutParams(0,dp(50),1);dd.setMargins(dp(8),0,0,0);drow.addView(disconnect,dd);
        TextView info=label("Device: "+Build.MANUFACTURER+" "+Build.MODEL+" • Android "+Build.VERSION.RELEASE+"\n🔒 Safety Kernel active • commands are authenticated, allowlisted and verification-gated",12);info.setTextColor(Color.rgb(148,163,184));root.addView(info);
    }

    private EditText field(String hint,boolean secret){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.rgb(100,116,139));e.setTextColor(Color.WHITE);e.setSingleLine(true);e.setPadding(dp(12),dp(8),dp(12),dp(8));if(secret)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);GradientDrawable g=new GradientDrawable();g.setColor(Color.rgb(15,23,42));g.setCornerRadius(dp(12));g.setStroke(dp(1),Color.rgb(51,65,85));e.setBackground(g);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(50));p.setMargins(0,dp(5),0,dp(5));e.setLayoutParams(p);return e;}
    private void connectDevice(){String base=apiUrl.getText().toString().trim().replaceAll("/+$","");String id=deviceIdInput.getText().toString().trim();String token=deviceTokenInput.getText().toString();if(base.isEmpty()||id.isEmpty()||token.length()<20){status.setText("Cloud URL, device ID and valid device token are required");return;}try{AndroidCommandService.start(this,base,id,token);status.setText("Device link starting • authenticated foreground service");}catch(Exception e){status.setText("Device link rejected • invalid configuration");}}
    private void addMessage(String who,String text){TextView v=label(who+"\n"+text,15);v.setPadding(dp(14),dp(12),dp(14),dp(12));v.setTextColor(who.equals("You")?Color.rgb(226,232,240):Color.rgb(191,219,254));GradientDrawable g=new GradientDrawable();g.setColor(who.equals("You")?Color.rgb(30,41,59):Color.rgb(20,39,65));g.setCornerRadius(dp(15));v.setBackground(g);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.setMargins(0,dp(5),0,dp(5));messages.addView(v,p);}
    private void initSpeech(){if(!SpeechRecognizer.isRecognitionAvailable(this)){status.setText("Speech recognition unavailable");return;}speechRecognizer=SpeechRecognizer.createSpeechRecognizer(this);speechRecognizer.setRecognitionListener(new RecognitionListener(){public void onReadyForSpeech(Bundle b){status.setText("Listening…");}public void onBeginningOfSpeech(){}public void onRmsChanged(float r){}public void onBufferReceived(byte[] b){}public void onEndOfSpeech(){status.setText("Thinking…");}public void onError(int e){status.setText("Speech error "+e);}public void onResults(Bundle r){ArrayList<String> x=r.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);if(x!=null&&!x.isEmpty()){transcript.setText(x.get(0));sendAssistant();}}public void onPartialResults(Bundle b){}public void onEvent(int e,Bundle b){}});}
    private void startListening(){if(speechRecognizer==null)initSpeech();if(speechRecognizer==null)return;Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,"te-IN");i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false);speechRecognizer.startListening(i);}
    @Override public void onInit(int code){if(code!=TextToSpeech.SUCCESS){status.setText("Voice unavailable");return;}int r=textToSpeech.setLanguage(new Locale("te","IN"));if(r==TextToSpeech.LANG_MISSING_DATA||r==TextToSpeech.LANG_NOT_SUPPORTED)r=textToSpeech.setLanguage(Locale.ENGLISH);ttsReady=r!=TextToSpeech.LANG_MISSING_DATA&&r!=TextToSpeech.LANG_NOT_SUPPORTED;textToSpeech.setSpeechRate(.88f);textToSpeech.setPitch(.82f);}
    private void speakText(String text){if(ttsReady&&!text.isEmpty()){Locale locale=Locale.forLanguageTag(responseLocale);if(textToSpeech.isLanguageAvailable(locale)>=TextToSpeech.LANG_AVAILABLE)textToSpeech.setLanguage(locale);else textToSpeech.setLanguage(Locale.ENGLISH);textToSpeech.speak(text,TextToSpeech.QUEUE_FLUSH,null,"aethon");status.setText("AETHON is speaking…");}}
    private void sendAssistant(){String text=transcript.getText().toString().trim();if(text.isEmpty()){status.setText("Type or speak a request first");return;}addMessage("You",text);String base=apiUrl==null?"":apiUrl.getText().toString().trim().replaceAll("/+$","");if(base.isEmpty())base="http://10.0.2.2:8000";status.setText("AETHON is thinking…");final String url=base;new Thread(()->{HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(url+"/v1/assistant/respond").openConnection();c.setRequestMethod("POST");c.setDoOutput(true);c.setConnectTimeout(8000);c.setReadTimeout(30000);c.setRequestProperty("Content-Type","application/json; charset=UTF-8");JSONObject o=new JSONObject();o.put("text",text);o.put("language","auto");if(sessionId!=null)o.put("session_id",sessionId);try(OutputStream out=c.getOutputStream()){out.write(o.toString().getBytes(StandardCharsets.UTF_8));}int code=c.getResponseCode();BufferedReader rd=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=rd.readLine())!=null)b.append(line);if(code>=400)throw new IllegalStateException("HTTP "+code);JSONObject res=new JSONObject(b.toString());sessionId=res.optString("session_id",sessionId);responseLocale=res.optString("language","te-IN");String answer=res.optString("response","");String mode=res.optString("mode","");handler.post(()->{lastAssistantText=answer;addMessage("✦ AETHON",answer+(mode.equals("ACTION")?"\n\nAction request • authorization pending":""));status.setText("AETHON replied • "+responseLocale);speakText(answer);});}catch(Exception e){handler.post(()->status.setText("Assistant connection failed • "+e.getMessage()));}finally{if(c!=null)c.disconnect();}}).start();}
    private void checkHealth(){String base=apiUrl==null?"http://10.0.2.2:8000":apiUrl.getText().toString().trim().replaceAll("/+$","");new Thread(()->{try{HttpURLConnection c=(HttpURLConnection)new URL(base+"/health").openConnection();int code=c.getResponseCode();handler.post(()->status.setText("API connected • HTTP "+code));c.disconnect();}catch(Exception e){handler.post(()->status.setText("API connection failed"));}}).start();}
    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==REQUEST_RECORD_AUDIO&&g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED)initSpeech();}
    @Override protected void onDestroy(){if(speechRecognizer!=null)speechRecognizer.destroy();if(textToSpeech!=null){textToSpeech.stop();textToSpeech.shutdown();}super.onDestroy();}
}
