// Per-locale type and cast for header.html and search.html: `?loc=<ASC locale>`.
// Headline lines mark the orange word with *…*. Copy adapts headline 1 of the approved screenshot
// translations (campaign-v10/localized/translations.json); ro, pl, uk, vi, th were written for this.
// Film names in the print chins and the date stamp stay as they are. en-US (no ?loc) is untouched.
const COPY = {
  "en-US":   ["Make tonight", "a *throwback.*", "Retro looks for nights with your people", "Vintage Camera"],
  "en-GB":   ["Make tonight", "a *throwback.*", "Retro looks for nights with your people", "Vintage Camera"],
  "es-ES":   ["Dale a esta noche", "un toque *retro.*", "Fotos retro para tus noches con amigos", "Cámara de fotos retro"],
  "es-MX":   ["Dale a esta noche", "un toque *retro.*", "Fotos retro para tus noches con amigos", "Cámara de fotos retro"],
  "fr-FR":   ["Donnez un air *rétro*", "à vos soirées.", "Des photos rétro pour vos soirées entre amis", "Appareil photo rétro"],
  "de-DE":   ["Gib dem Abend", "einen *Retro-Look.*", "Retro-Fotos für Nächte mit deinen Leuten", "Retro-Fotokamera"],
  "it":      ["Dai un tocco *rétro*", "alla serata.", "Foto rétro per le serate con i tuoi amici", "Fotocamera rétro"],
  "pt-BR":   ["Dê um toque *retrô*", "à noite.", "Fotos retrô para as noites com a sua turma", "Câmera retrô"],
  "nl-NL":   ["Geef je avond", "een *retrolook.*", "Retrofoto’s van avonden met jouw mensen", "Retrofotocamera"],
  "id":      ["Bikin malam ini", "terasa *retro.*", "Foto retro untuk malam bersama teman-temanmu", "Kamera foto retro"],
  "tr":      ["Geceye *retro*", "bir hava kat.", "Arkadaşlarınla gecelerine retro fotoğraflar", "Retro fotoğraf kamerası"],
  "ro":      ["Dă serii de azi", "un aer *retro.*", "Fotografii retro pentru serile cu prietenii", "Cameră foto retro"],
  "pl":      ["Nadaj wieczorowi", "klimat *retro.*", "Zdjęcia retro na wieczory ze znajomymi", "Aparat retro"],
  "ru":      ["Придай вечеру", "*ретростиль.*", "Ретрофото для вечеров со своими", "Ретрофотокамера"],
  "uk":      ["Додай вечору", "*ретростилю.*", "Ретрофото для вечорів зі своїми", "Ретрофотокамера"],
  "vi":      ["Biến đêm nay", "thành ảnh *retro.*", "Ảnh retro cho những đêm bên bạn bè", "Máy ảnh retro"],
  "th":      ["ทำให้คืนนี้", "เป็นภาพ*ย้อนยุค*", "ภาพย้อนยุคสำหรับคืนกับเพื่อนๆ", "กล้องถ่ายภาพย้อนยุค"],
  "ar-SA":   ["امنح ليلتك", "*طابعًا قديمًا.*", "صور بطابع قديم للياليك مع أصحابك", "كاميرا صور بطابع قديم"],
  "hi":      ["आज की रात को", "*रेट्रो* रंग दें।", "दोस्तों के साथ बिताई रातों के लिए रेट्रो फ़ोटो", "रेट्रो फ़ोटो कैमरा"],
  "ja":      ["今夜を", "*レトロ*に残そう。", "仲間と過ごす夜を、レトロな写真に。", "レトロ写真カメラ"],
  "ko":      ["오늘 밤을", "*레트로*로 담아봐.", "친구들과의 밤을 레트로 사진으로.", "레트로 사진 카메라"],
  "zh-Hans": ["把今晚拍成", "*复古*回忆。", "和朋友共度的夜晚，用复古照片记录。", "复古相机"],
  "zh-Hant": ["把今晚拍成", "*復古*回憶。", "和朋友共度的夜晚，用復古照片記錄。", "復古相機"],
};
// Type face where VCR OSD Mono (Basic Latin + Latin-1 only) lacks glyphs: Fusion Pixel (OFL) keeps the
// pixel look for Latin Extended, Cyrillic and CJK; system faces where no pixel font covers the script.
const FACE = {
  "tr": "FusionLatin", "ro": "FusionLatin", "pl": "FusionLatin", "ru": "FusionLatin", "uk": "FusionLatin",
  "ja": "FusionJA", "ko": "FusionKO", "zh-Hans": "FusionSC", "zh-Hant": "FusionTC",
  "vi": "Monaco", "th": "Ayuthaya", "ar-SA": "'Geeza Pro'", "hi": "'Kohinoor Devanagari'",
};
// Storefronts with their own cast (same scenes and films, see campaign-v10/regions).
const REGION = {
  "ja": "east-asia", "ko": "east-asia", "zh-Hans": "east-asia", "zh-Hant": "east-asia", "vi": "east-asia", "th": "east-asia",
  "es-MX": "latam", "pt-BR": "latam", "hi": "south-asia", "id": "south-asia", "ar-SA": "middle-east",
};
const LANG = { "zh-Hans": "zh-CN", "zh-Hant": "zh-TW", "ar-SA": "ar" };

window.photoDir = "photos/";
(() => {
  const loc = new URLSearchParams(location.search).get("loc");
  if (!loc || loc === "en-US") return;
  const c = COPY[loc];
  if (!c) throw new Error("no copy for " + loc);
  document.documentElement.lang = LANG[loc] ?? loc.split("-")[0];   // tr: i → İ when uppercased
  const esc = (s) => s.replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[m]);
  const hot = (s) => esc(s).replace(/\*(.+?)\*/g, '<span class="hot">$1</span>');
  // The type stack keeps en-US's gaps: capture them before the copy changes, re-flow after fitting.
  const desk = document.querySelector(".desk");
  const stamps = [...desk.querySelectorAll(".stamp")].filter((e) => !e.classList.contains("label"));
  const head = desk.querySelector('[data-copy="headline"]');
  const below = stamps.filter((e) => e.offsetTop > head.offsetTop);
  const gaps = below.map((e, i) => e.offsetTop - (i ? below[i - 1].offsetTop + below[i - 1].offsetHeight : head.offsetTop + head.offsetHeight));
  const set = (k, html) => document.querySelectorAll(`[data-copy="${k}"]`).forEach((e) => (e.innerHTML = html));
  set("headline", hot(c[0]) + "<br>" + hot(c[1]));
  set("sub", esc(c[2]));
  set("eyebrow", "Last Summer / " + esc(c[3]));
  const face = FACE[loc];
  if (face) document.querySelectorAll("[data-copy]").forEach((e) => (e.style.fontFamily = `${face}, VCR, sans-serif`));
  if (face && !face.startsWith("Fusion")) document.querySelectorAll("[data-copy]").forEach((e) => { e.style.fontWeight = 700; e.style.letterSpacing = "0"; });
  if (loc === "ar-SA") document.querySelectorAll("[data-copy]").forEach((e) => { e.dir = "rtl"; e.style.width = e.dataset.max + "px"; e.style.textAlign = "right"; });
  if (REGION[loc]) {
    window.photoDir = `photos/${REGION[loc]}/`;
    document.querySelectorAll('img[src^="photos/"]').forEach((i) => (i.src = i.getAttribute("src").replace("photos/", window.photoDir)));
  }
  // Shrink any line that runs past its box (data-max, CSS px) once the fonts are in.
  document.fonts.ready.then(() => document.querySelectorAll("[data-max]").forEach((e) => {
    let s = parseFloat(getComputedStyle(e).fontSize);
    e.style.whiteSpace = "nowrap";
    const width = () => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect().width; };
    while (width() > +e.dataset.max && s > 10) { s -= 1; e.style.fontSize = s + "px"; }
  })).then(() => {
    let y = head.offsetTop + head.offsetHeight;
    below.forEach((e, i) => { e.style.top = y + gaps[i] + "px"; y = y + gaps[i] + e.offsetHeight; });
  });
})();
