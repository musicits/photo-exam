/* 사진기능사 오답노트 — 기기 사이 주고받기
 *
 * 쓰는 법은 셋뿐이다.
 *   POST /new          새 코드와 열쇠를 받는다
 *   PUT  /s/<코드>      그 코드 자리에 기록을 덮어쓴다 (열쇠 필요)
 *   GET  /s/<코드>      그 코드 자리의 기록을 읽는다
 *
 * 코드는 30일 동안 아무도 건드리지 않으면 저절로 사라진다.
 * 사람을 가리는 값은 받지 않는다. 코드와 열쇠가 전부다.
 */

const ORIGIN = "https://tools.musicits.com";
const TTL = 60 * 60 * 24 * 30;        // 30일
const MAX = 512 * 1024;               // 기록 한 덩이의 최대 크기
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";  // 헷갈리는 0·O·1·I 는 뺀다

function rand(n) {
  const buf = new Uint8Array(n);
  crypto.getRandomValues(buf);
  return [...buf].map((b) => ALPHABET[b % ALPHABET.length]).join("");
}

function cors(extra = {}) {
  return {
    "access-control-allow-origin": ORIGIN,
    "access-control-allow-methods": "GET,PUT,POST,OPTIONS",
    "access-control-allow-headers": "content-type,x-key",
    "access-control-max-age": "86400",
    ...extra,
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: cors({ "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }),
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors() });

    // 새 코드 만들기
    if (request.method === "POST" && url.pathname === "/new") {
      let code = "";
      for (let i = 0; i < 5; i++) {              // 이미 쓰는 코드면 다시 뽑는다
        code = rand(6);
        if (!(await env.NOTES.get("k:" + code))) break;
        code = "";
      }
      if (!code) return json({ error: "코드를 만들지 못했습니다. 잠시 뒤 다시 눌러 주세요." }, 503);

      const key = rand(10);
      await env.NOTES.put("k:" + code, key, { expirationTtl: TTL });
      await env.NOTES.put("d:" + code, "{}", { expirationTtl: TTL });
      return json({ code, key });
    }

    const m = url.pathname.match(/^\/s\/([A-Z0-9]{6})$/);
    if (!m) return json({ error: "없는 주소입니다." }, 404);
    const code = m[1];

    // 읽기 — 코드만 있으면 된다
    if (request.method === "GET") {
      const data = await env.NOTES.get("d:" + code);
      if (data === null) return json({ error: "없는 코드입니다. 30일 넘게 안 쓰면 지워집니다." }, 404);
      return json({ code, data: JSON.parse(data) });
    }

    // 쓰기 — 열쇠가 맞아야 한다
    if (request.method === "PUT") {
      const key = await env.NOTES.get("k:" + code);
      if (key === null) return json({ error: "없는 코드입니다." }, 404);
      if (request.headers.get("x-key") !== key) return json({ error: "열쇠가 맞지 않습니다." }, 403);

      const body = await request.text();
      if (body.length > MAX) return json({ error: "기록이 너무 큽니다." }, 413);
      try { JSON.parse(body); } catch { return json({ error: "기록을 읽지 못했습니다." }, 400); }

      // 건드릴 때마다 30일을 다시 센다
      await env.NOTES.put("d:" + code, body, { expirationTtl: TTL });
      await env.NOTES.put("k:" + code, key, { expirationTtl: TTL });
      return json({ ok: true, savedAt: Date.now() });
    }

    return json({ error: "안 되는 요청입니다." }, 405);
  },
};
