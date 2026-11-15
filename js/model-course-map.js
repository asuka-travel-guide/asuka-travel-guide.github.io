// model-course-map.js
//
// 駐車場リンク・レンタサイクルのカードを押したとき、
// モデルコースページ内の Google マイマップ（iframe）をその場所に拡大して、地図まで移動する。
//
// リンク側に付ける data 属性
//   data-map-target  … 対象の iframe の id（例: main-map-drive-full）※必須
//   data-ll          … 拡大する位置「緯度,経度」（例: 34.45170,135.80380）※無い場合は地図まで移動するだけ
//   data-z           … 拡大率（省略時 18）
//
// 拡大するのは、iframe に最初から入っている地図そのもの（地図の切り替えはしない）。
// JS が動かない環境では、リンクは従来どおり href へ移動する。
document.addEventListener("DOMContentLoaded", () => {
  const reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 地図の iframe が読み込み済みかどうかを覚えておく
  document.querySelectorAll(".model-course-map iframe").forEach((f) => {
    f.addEventListener("load", () => {
      f.dataset.mapLoaded = "1";
    });
  });

  // iframe ごとの「最初の地図 URL」
  const originals = new Map();

  // 地図を切り替える。
  //  ・まだ読み込まれていない iframe（loading="lazy" で待機中）は、遅延読み込みを解除して
  //    src を直接書き換える。location.replace だと、あとから始まる遅延読み込みに上書きされるため。
  //  ・読み込み済みなら、履歴を増やさないよう location.replace を使う。
  function navigate(iframe, url) {
    if (!iframe.dataset.mapLoaded) {
      iframe.loading = "eager";
      iframe.src = url;
      return;
    }
    try {
      iframe.contentWindow.location.replace(url);
    } catch (e) {
      iframe.src = url;
    }
  }

  function buildUrl(base, ll, z) {
    const u = new URL(base, window.location.href);
    u.searchParams.set("ll", ll);
    u.searchParams.set("z", z);
    return u.toString();
  }

  document.addEventListener("click", (e) => {
    const link = e.target.closest("a[data-map-target]");
    if (!link || e.defaultPrevented) return;

    const iframe = document.getElementById(link.dataset.mapTarget);
    if (!iframe) return; // 対象が無ければ従来の動き

    e.preventDefault();

    const ll = (link.dataset.ll || "").trim();
    if (ll) {
      if (!originals.has(iframe)) originals.set(iframe, iframe.getAttribute("src"));
      const z = (link.dataset.z || "18").trim();
      navigate(iframe, buildUrl(originals.get(iframe), ll, z));
    }

    const section = iframe.closest(".model-course-map") || iframe;
    section.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  });
});
