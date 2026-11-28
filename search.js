/* Lovely site search: a search button in the header that opens a search panel.
   Finds products and pages, and answers questions from the FAQ (loaded from faq.html). */
(function () {
  "use strict";
  var me = document.currentScript;
  var BASE = me ? me.src.replace(/search\.js(\?.*)?$/, "") : "";
  var u = function (p) { return BASE + p; };

  var ITEMS = [
    { t: "Lovely Chocolate", d: "Like a chocolate milkshake. 30g or 50g protein.", url: "shop.html", img: "img/b_choc.webp?v=9", k: "shake chocolate cocoa milkshake flavor 30g 50g protein bottle" },
    { t: "Lovely Vanilla", d: "The everyday base. Great in coffee or a Ninja Creami.", url: "shop.html", img: "img/b_van.webp?v=9", k: "shake vanilla flavor coffee creami 30g 50g protein bottle" },
    { t: "Lovely Cookie Butter", d: "Spiced speculoos cookie butter in a sweet cream base.", url: "shop.html", img: "img/b_cbutter.webp?v=9", k: "shake cookie butter biscoff speculoos dessert flavor 30g 50g protein bottle" },
    { t: "Lovely Matcha", d: "The coffee-shop order with 30g protein. Natural caffeine from matcha.", url: "shop.html", img: "img/b_matcha.webp?v=9", k: "shake matcha green tea latte flavor caffeine 30g 50g protein bottle" },
    { t: "Lovely Peanut Butter", d: "Salty-sweet, like a peanut butter milkshake. Contains peanuts.", url: "shop.html", img: "img/b_pb.webp?v=9", k: "shake peanut butter pb nut allergy flavor 30g 50g protein bottle" },
    { t: "Lovely 50g", d: "The bigger coral 16oz bottle with 50g protein.", url: "shop.html", img: "img/b_choc.webp?v=9", k: "50g fifty big bigger coral bottle 16oz more protein bulk gym" },
    { t: "Build a box", d: "Mix flavors and sizes in a 24-pack. Subscribe and save, skip anytime.", url: "shop.html", k: "shop buy order box 24 pack 12 pack subscribe subscription price cost save delivery shipping" },
    { t: "Lovely Creatine sticks", d: "Flavorless stirs into any shake. Four flavors for water.", url: "products.html#creatine-info", img: "img/creatine/elec_lineup_sm.webp?v=2", k: "creatine stick packet electrolytes monohydrate magnesium potassium flavorless blue raspberry pina colada sour apple watermelon water" },
    { t: "Lovely Creatine Gummies", d: "Heart-shaped creatine gummies, 60 a jar, in five flavors.", url: "products.html#gummies-info", img: "img/gummies/strawberry_sm.webp", k: "creatine gummies gummy candy chew strawberry blue raspberry watermelon pina colada sour apple jar" },
    { t: "Protein ice cream pints", d: "Dessert pints with 30g protein each.", url: "products.html#icecream-info", k: "ice cream pint dessert frozen sorbet protein" },
    { t: "Ninja Creami recipes", d: "Turn a Lovely into protein ice cream at home.", url: "products.html#creami", k: "ninja creami recipe ice cream homemade freeze pint milkshake sorbet" },
    { t: "All products", d: "Creatine, gummies, ice cream pints and recipes.", url: "products.html", k: "products everything catalog" },
    { t: "Lovely Pass", d: "One membership for your box and the Lovely fridge. Member prices and points.", url: "index.html#lovelypass", img: "img/shot_pass.webp?v=5", k: "pass membership member points rewards free shake qr code app" },
    { t: "Find a Lovely fridge", d: "Grab a cold Lovely at studios, gyms and campuses.", url: "index.html#find", img: "img/shot_map.webp?v=5", k: "fridge find near me location map store where buy cold studio gym campus" },
    { t: "Stock Lovely at your studio", d: "Own a studio or gym? Get a Lovely fridge.", url: "index.html#host", k: "studio owner gym host fridge wholesale stock business partner" },
    { t: "Become an affiliate", d: "Creators and instructors earn commission.", url: "affiliate.html", k: "affiliate ambassador creator influencer commission earn partner code" },
    { t: "About Lovely", d: "Why we made the shake you actually want to drink.", url: "about.html", k: "about story founder company brand who" },
    { t: "FAQ", d: "Ingredients, shipping, subscriptions and more.", url: "faq.html", k: "faq questions help support contact" },
    { t: "Blog", d: "Protein, recipes and more.", url: "blog.html", k: "blog articles read" },
    { t: "Your account", d: "Subscriptions, payment, points and fridge history.", url: "account.html", k: "account login sign in profile subscription manage cancel skip" },
    { t: "Your cart", d: "See what's in your box.", url: "cart.html", k: "cart checkout bag" }
  ];

  var STOP = "a an the is are am do does did can could would should will i im i'm me my you your it its of to in on for and or with what how why when where which who this that there be have has any about lovely".split(" ");
  var SYN = { cost: "price", costs: "price", expensive: "price", cheap: "price", pricing: "price", dollars: "price",
    sweet: "sweetened", sweetener: "sweetened", sweeteners: "sweetened", sugars: "sugar", sugary: "sugar",
    dairy: "lactose", milk: "lactose", bloat: "lactose", bloating: "lactose", vegan: "lactose",
    ship: "shipping", shipped: "shipping", deliver: "shipping", delivery: "shipping",
    cals: "calories", calorie: "calories", kcal: "calories", proteins: "protein",
    flavour: "flavor", flavours: "flavors", taste: "flavor", tastes: "flavor",
    gummy: "gummies", stick: "sticks", packet: "sticks", packets: "sticks",
    cancel: "subscription", subscribe: "subscription", skip: "subscription", pause: "subscription",
    pregnant: "pregnancy", nursing: "pregnancy", breastfeeding: "pregnancy",
    nut: "peanut", nuts: "peanut", allergy: "allergen", allergies: "allergen",
    near: "fridge", location: "fridge", locations: "fridge" };

  function words(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9\s]/g, " ").split(/\s+/)
      .filter(function (w) { return w && STOP.indexOf(w) < 0; })
      .map(function (w) { return SYN[w] || w; });
  }
  function has(hay, w) { var a = (" " + hay + " "), b = w.replace(/s$/, ""); return a.indexOf(" " + w + " ") >= 0 || a.indexOf(" " + b + " ") >= 0 || a.indexOf(" " + b + "s ") >= 0 || (w.length > 4 && a.indexOf(" " + w) >= 0); }
  function score(item, q) {
    var t = words(item.t).join(" "), b = words((item.k || "") + " " + item.d).join(" "), s = 0, hit = 0;
    q.forEach(function (w) {
      var x = 0;
      if (has(t, w)) x += 3;
      if (has(b, w)) x += 1;
      if (x) hit++;
      s += x;
    });
    return hit ? s * (hit / q.length) : 0;
  }

  // extra words people use for each FAQ question, so plain-language questions find the right answer
  var FAQ_K = [
    ["What is Lovely?", "protein grams calories nutrition healthy iron collagen"],
    ["What is Lovely 50g?", "50g protein more bigger coral gym"],
    ["Is Lovely lactose-free?", "lactose bloating stomach digest"],
    ["What else is in it", "vitamins iron collagen ingredients nutrition"],
    ["How much does it cost?", "price buy order single bottle box"],
    ["Is there a subscription discount?", "subscription save deal coupon"],
    ["How does reserving a box work?", "subscription order charged ship skip pause cancel"],
    ["Where are Lovely fridges?", "buy store near fridge"],
    ["Can I mix flavors", "box flavors mix shipping order"]
  ];
  var FAQ = null, faqLoading = null;
  function loadFaq() {
    if (FAQ) return null; if (faqLoading) return faqLoading;
    faqLoading = fetch(u("faq.html")).then(function (r) { return r.text(); }).then(function (html) {
      var doc = new DOMParser().parseFromString(html, "text/html");
      FAQ = Array.prototype.map.call(doc.querySelectorAll(".acc details"), function (d) {
        var q = d.querySelector("summary"), a = d.querySelector(".ans");
        var t = q ? q.textContent.trim().replace(/\s+/g, " ") : "", k = ""; FAQ_K.forEach(function (x) { if (t.indexOf(x[0]) === 0) k = x[1]; });
        return { t: t, d: a ? a.textContent.trim().replace(/\s+/g, " ") : "", k: k, url: "faq.html" };
      }).filter(function (x) { return x.t; });
    }).catch(function () { FAQ = []; });
    return faqLoading;
  }

  var css = "" +
    ".srch-btn{display:grid;place-items:center;width:44px;height:44px;border:0;border-radius:50%;background:transparent;color:var(--fg,#fff);cursor:pointer;flex:none;-webkit-tap-highlight-color:transparent}" +
    ".srch-btn .sav{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:var(--surface,#f06a50);transition:transform .3s cubic-bezier(.34,1.56,.64,1)}" +
    ".srch-btn:active .sav{transform:scale(.9)}" +
    ".srch-btn.srch-m{display:none}" +
    "@media (max-width:1100px){.srch-btn.srch-m{display:grid}.srch-btn.srch-d{display:none}}" +
    ".srch-scrim{position:fixed;inset:0;z-index:95;background:rgba(90,20,10,.42);opacity:0;transition:opacity .25s}" +
    ".srch-open .srch-scrim{opacity:1}" +
    ".srch{position:fixed;z-index:96;left:50%;top:calc(14px + env(safe-area-inset-top,0px));width:min(680px,calc(100vw - 24px));max-height:calc(100dvh - 28px - env(safe-area-inset-top,0px));display:flex;flex-direction:column;background:var(--bg,#ea5a41);border-radius:26px;box-shadow:0 30px 70px -20px rgba(140,30,14,.45);transform:translate(-50%,-14px) scale(.98);opacity:0;transition:transform .35s cubic-bezier(.22,1,.36,1),opacity .25s;overflow:hidden}" +
    ".srch-open .srch{transform:translate(-50%,0);opacity:1}" +
    ".srch-bar{display:flex;align-items:center;gap:10px;margin:12px;padding:0 8px 0 16px;height:56px;border-radius:999px;background:#fff;color:#d94a31;flex:none}" +
    ".srch-bar svg{flex:none;opacity:.7}" +
    ".srch-bar input{flex:1;min-width:0;border:0;outline:none;background:none;font:500 17px/1.2 var(--body,system-ui);color:#d94a31}" +
    ".srch-bar input::placeholder{color:rgba(200,55,32,.6)}" +
    ".srch-x{border:0;background:var(--surface,#f06a50);color:#fff;width:38px;height:38px;border-radius:50%;font-size:22px;line-height:1;cursor:pointer;flex:none}" +
    ".srch-body{overflow-y:auto;padding:0 12px 14px;overscroll-behavior:contain}" +
    ".srch-h{font:700 11.5px/1 var(--body,system-ui);letter-spacing:.12em;text-transform:uppercase;color:#fff;margin:14px 6px 8px}" +
    ".srch-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 4px}" +
    ".srch-chips button{border:0;border-radius:999px;padding:9px 13px;background:rgba(255,255,255,.16);color:#fff;font:600 13.5px/1 var(--body,system-ui);cursor:pointer}" +
    ".srch-ans{background:#f06a50;border:1.5px solid rgba(255,255,255,.3);border-radius:18px;padding:16px 18px;color:#fff}" +
    ".srch-ans>b{display:block;font:700 18px/1.25 var(--display,Georgia,serif);color:#fff;margin-bottom:6px}" +
    ".srch-ans p{margin:0;font-size:15px;line-height:1.5;color:#fff}" +
    ".srch-ans a{display:inline-block;margin-top:8px;font:700 13.5px var(--body,system-ui);color:#fff}" +
    ".srch-list{display:grid;gap:6px}" +
    ".srch-it{display:grid;grid-template-columns:44px 1fr;gap:12px;align-items:center;padding:8px 10px;border-radius:16px;background:rgba(255,255,255,.16);text-decoration:none;color:#fff}" +
    ".srch-it:hover,.srch-it:focus-visible{background:rgba(255,255,255,.28);outline:none}" +
    ".srch-it .ic{width:44px;height:44px;border-radius:12px;background:rgba(255,255,255,.16);display:grid;place-items:center;overflow:hidden}" +
    ".srch-it .ic img{width:100%;height:100%;object-fit:contain}" +
    ".srch-it .tx>b{display:block;font:700 15px/1.25 var(--body,system-ui)}" +
    ".srch-it .tx>span{display:block;font-size:13px;line-height:1.35;color:#fff}" +
    ".srch-faq{display:block;padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.16);text-decoration:none;color:#fff}" +
    ".srch-faq:hover,.srch-faq:focus-visible{background:rgba(255,255,255,.28);outline:none}" +
    ".srch-faq>b{display:block;font:700 14.5px/1.3 var(--body,system-ui)}" +
    ".srch-faq>span{display:block;font-size:13px;line-height:1.4;color:#fff;margin-top:3px}" +
    ".srch-bar input::-webkit-search-cancel-button{-webkit-appearance:none;display:none}" +
    ".srch-none{padding:14px 8px;color:#fff;font-size:15px}" +
    ".srch-none a{color:#fff;font-weight:700}" +
    "html.srch-lock,html.srch-lock body{overflow:hidden}" +
    "@media (max-width:560px){.srch{top:calc(8px + env(safe-area-inset-top,0px));width:calc(100vw - 16px);border-radius:22px}.srch-bar{margin:10px;height:52px}}" +
    "@media (prefers-reduced-motion:reduce){.srch,.srch-scrim{transition:none}}";

  var ICON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="10.8" cy="10.8" r="6.3"/><path d="M15.6 15.6 20 20"/></svg>';
  var SUGGEST = ["How much protein is in it?", "Is it lactose-free?", "What is it sweetened with?", "Creatine gummies", "Lovely Pass", "Find a fridge"];

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function cut(s, n) { return s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + "…" : s; }

  var root, input, body, lastFocus;
  function build() {
    root = document.createElement("div");
    root.innerHTML = '<div class="srch-scrim" data-srch-close></div><div class="srch" role="dialog" aria-modal="true" aria-label="Search Lovely">' +
      '<form class="srch-bar" role="search">' + ICON + '<label class="sr" for="srch-q" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Search Lovely or ask a question</label>' +
      '<input id="srch-q" type="search" autocomplete="off" enterkeyhint="search" placeholder="Search products or ask a question">' +
      '<button type="button" class="srch-x" data-srch-close aria-label="Close search">&times;</button></form>' +
      '<div class="srch-body" aria-live="polite"></div></div>';
    root.hidden = true;
    document.body.appendChild(root);
    input = root.querySelector("input"); body = root.querySelector(".srch-body");
    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-srch-close]")) { close(); return; }
      var c = e.target.closest("[data-q]"); if (c) { input.value = c.dataset.q; run(); input.focus(); }
    });
    root.querySelector("form").addEventListener("submit", function (e) { e.preventDefault(); var a = body.querySelector("a"); if (a && input.value.trim()) a.click(); });
    input.addEventListener("input", run);
    root.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { close(); return; }
      if (e.key === "Tab") {
        var f = root.querySelectorAll("input,button,a"); if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  function empty() {
    body.innerHTML = '<p class="srch-h">Try</p><div class="srch-chips">' + SUGGEST.map(function (s) { return '<button type="button" data-q="' + esc(s) + '">' + esc(s) + "</button>"; }).join("") + "</div>" +
      '<p class="srch-h">Popular</p><div class="srch-list">' + ITEMS.slice(7, 9).concat(ITEMS[6], ITEMS[12]).map(card).join("") + "</div>";
  }
  function card(it) {
    return '<a class="srch-it" href="' + esc(u(it.url)) + '"><span class="ic">' + (it.img ? '<img src="' + esc(u(it.img)) + '" alt="" loading="lazy">' : ICON) + "</span><span class=\"tx\"><b>" + esc(it.t) + "</b><span>" + esc(it.d) + "</span></span></a>";
  }

  function run() {
    var raw = input.value.trim();
    if (!raw) { empty(); return; }
    var q = words(raw); if (!q.length) q = [raw.toLowerCase()];
    var prods = ITEMS.map(function (it) { return { it: it, s: score(it, q) }; }).filter(function (x) { return x.s > 0; }).sort(function (a, b) { return b.s - a.s; }).slice(0, 5);
    var faqs = (FAQ || []).map(function (it) { var s = score(it, q); return { it: it, s: s }; }).filter(function (x) { return x.s > 0.9; }).sort(function (a, b) { return b.s - a.s; }).slice(0, 4);
    // "how much protein" should answer with the basics (30g / 50g), not the vitamins question
    if (/protein/i.test(raw) && /(how much|how many|grams|\bg\b)/i.test(raw) && FAQ) {
      var basics = FAQ.filter(function (f) { return f.t.indexOf("What is Lovely?") === 0; })[0];
      if (basics) faqs = [{ it: basics, s: 99 }].concat(faqs.filter(function (x) { return x.it !== basics; }));
    }
    var looksLikeQuestion = /\?$|^(how|what|is|are|does|do|can|why|when|where|which|who|will|should)\b/i.test(raw) || q.length >= 3;
    var html = "";
    if (faqs.length && (looksLikeQuestion || faqs[0].s >= (prods[0] ? prods[0].s : 0))) {
      var top = faqs[0].it;
      html += '<p class="srch-h">Answer</p><div class="srch-ans"><b>' + esc(top.t) + "</b><p>" + esc(cut(top.d, 420)) + '</p><a href="' + esc(u("faq.html")) + '">More in the FAQ →</a></div>';
      faqs = faqs.slice(1);
    }
    if (prods.length) html += '<p class="srch-h">Products and pages</p><div class="srch-list">' + prods.map(function (x) { return card(x.it); }).join("") + "</div>";
    if (faqs.length) html += '<p class="srch-h">Related questions</p><div class="srch-list">' + faqs.map(function (x) { return '<a class="srch-faq" href="' + esc(u("faq.html")) + '"><b>' + esc(x.it.t) + "</b><span>" + esc(cut(x.it.d, 140)) + "</span></a>"; }).join("") + "</div>";
    if (!html) html = FAQ ? '<p class="srch-none">Nothing found for "' + esc(raw) + '". Try another word, or browse the <a href="' + esc(u("faq.html")) + '">FAQ</a>.</p>' : '<p class="srch-none">Searching…</p>';
    body.innerHTML = html;
  }

  function open() {
    if (!root) build();
    lastFocus = document.activeElement;
    root.hidden = false;
    document.documentElement.classList.add("srch-lock");
    requestAnimationFrame(function () { root.classList.add("srch-open"); });
    input.value = ""; empty();
    setTimeout(function () { input.focus(); }, 30);
    var p = loadFaq(); if (p) p.then(function () { if (input.value.trim()) run(); });
  }
  function close() {
    if (!root || root.hidden) return;
    root.classList.remove("srch-open");
    document.documentElement.classList.remove("srch-lock");
    setTimeout(function () { root.hidden = true; }, 260);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function makeBtn(cls) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "srch-btn press " + cls; b.setAttribute("aria-label", "Search");
    b.innerHTML = '<span class="sav" aria-hidden="true">' + ICON + "</span>";
    b.addEventListener("click", open);
    return b;
  }
  function addButton() {
    if (!document.getElementById("srch-css")) { var st = document.createElement("style"); st.id = "srch-css"; st.textContent = css; document.head.appendChild(st); }
    document.querySelectorAll("header.top").forEach(function (h) {
      if (h.querySelector(".srch-btn")) return;
      var r = h.querySelector(".right"); if (!r) return;
      r.insertBefore(makeBtn("srch-d"), r.firstChild);
      var bg = h.querySelector(".burger");
      if (bg) bg.parentNode.insertBefore(makeBtn("srch-m"), bg.nextSibling);
    });
  }
  document.addEventListener("keydown", function (e) {
    var t = e.target, typing = t && (t.isContentEditable || /^(input|textarea|select)$/i.test(t.tagName));
    if (!typing && (e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"))) { e.preventDefault(); open(); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", addButton); else addButton();
  window.LovelySearch = { open: open, close: close };
})();
