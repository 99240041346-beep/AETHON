package ai.aethon.android;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Converts org.json objects without relying on newer JSONObject.toMap(). */
public final class JsonObjectArguments {
    private JsonObjectArguments() {}

    public static Map<String, Object> toMap(JSONObject object) {
        if (object == null) return Collections.emptyMap();
        Map<String, Object> result = new HashMap<>();
        java.util.Iterator<String> keys = object.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            result.put(key, unwrap(object.opt(key)));
        }
        return result;
    }

    private static Object unwrap(Object value) {
        if (value instanceof JSONObject) return toMap((JSONObject) value);
        if (value instanceof JSONArray) {
            JSONArray array = (JSONArray) value;
            List<Object> result = new ArrayList<>();
            for (int i = 0; i < array.length(); i++) result.add(unwrap(array.opt(i)));
            return result;
        }
        return value == JSONObject.NULL ? null : value;
    }
}
