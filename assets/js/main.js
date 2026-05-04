(function () {
  "use strict";

  var navToggle = document.querySelector(".nav-toggle");
  var siteNav = document.querySelector(".site-nav");

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", function () {
      var open = siteNav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      navToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });

    siteNav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 767px)").matches) {
          siteNav.classList.remove("is-open");
          navToggle.setAttribute("aria-expanded", "false");
          navToggle.setAttribute("aria-label", "Open menu");
        }
      });
    });
  }

  /* Portfolio category filter */
  var filterBar = document.querySelector("[data-filter-bar]");
  if (filterBar) {
    var buttons = filterBar.querySelectorAll(".filter-btn");
    var cards = document.querySelectorAll("[data-project-card]");

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cat = btn.getAttribute("data-filter") || "all";

        buttons.forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });

        cards.forEach(function (card) {
          var c = card.getAttribute("data-category");
          var show = cat === "all" || c === cat;
          card.classList.toggle("is-hidden", !show);
        });
      });
    });
  }

  /* Hero thumbnail carousel (manifest JSON + Public Thumbnails folder) */
  function encodePathSegments(dir) {
    return dir
      .replace(/\\/g, "/")
      .replace(/^\/+|\/+$/g, "")
      .split("/")
      .map(function (seg) {
        return encodeURIComponent(seg);
      })
      .join("/");
  }

  function thumbnailUrl(dir, filename) {
    return encodePathSegments(dir) + "/" + encodeURIComponent(filename);
  }

  function altFromFilename(name) {
    var cleaned = name
      .replace(/^\d+_Workbook thumbnail,\s*/i, "")
      .replace(/\.(png|jpe?g|webp)$/i, "")
      .trim();
    return cleaned ? cleaned + " — Tableau workbook preview" : "Tableau workbook preview";
  }

  function shuffleInPlace(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = arr[i];
      arr[i] = arr[j];
      arr[j] = t;
    }
    return arr;
  }

  function parseNonNegInt(v) {
    if (v == null || v === "") return null;
    var n = parseInt(String(v), 10);
    if (isNaN(n) || n < 0) return null;
    return n;
  }

  function formatStat(n) {
    if (n == null) return "";
    return n.toLocaleString("en-GB");
  }

  function normalizeCarouselEntry(raw, dir) {
    if (typeof raw === "string") {
      var altStr = altFromFilename(raw);
      var titleFromFile = altStr.replace(/\s*—\s*Tableau workbook preview\s*$/i, "").trim();
      return {
        src: thumbnailUrl(dir, raw),
        alt: altStr,
        href: null,
        title: titleFromFile,
        favourites: null,
        views: null,
      };
    }
    if (raw && typeof raw === "object" && raw.image) {
      var imgPath = String(raw.image);
      var base = imgPath.split("/").pop() || "";
      var altText = typeof raw.alt === "string" && raw.alt ? raw.alt : altFromFilename(base);
      var hrefVal = raw.href != null && String(raw.href).trim() ? String(raw.href).trim() : null;
      var titleVal = typeof raw.title === "string" && raw.title ? raw.title : "";
      return {
        src: imgPath,
        alt: altText,
        href: hrefVal,
        title: titleVal,
        favourites: parseNonNegInt(raw.numberOfFavorites),
        views: parseNonNegInt(raw.viewCount),
      };
    }
    return null;
  }

  var carouselRoot = document.querySelector("[data-carousel]");
  if (carouselRoot) {
    var manifestUrl = carouselRoot.getAttribute("data-carousel-manifest") || "";
    var thumbDir = carouselRoot.getAttribute("data-carousel-dir") || "assets/Public Thumbnails";
    var intervalMs = parseInt(carouselRoot.getAttribute("data-carousel-interval") || "5500", 10);
    var slides = carouselRoot.querySelectorAll(".hero-carousel-slide");
    var fallbackEl = carouselRoot.querySelector("[data-carousel-fallback]");
    var linkEl = carouselRoot.querySelector("[data-carousel-link]");
    var metaEl = carouselRoot.querySelector("[data-carousel-meta]");
    var titleEl = carouselRoot.querySelector("[data-carousel-title]");
    var statsEl = carouselRoot.querySelector("[data-carousel-stats]");
    var favWrap = carouselRoot.querySelector("[data-carousel-favourites-wrap]");
    var viewsWrap = carouselRoot.querySelector("[data-carousel-views-wrap]");
    var favVal = carouselRoot.querySelector("[data-carousel-favourites]");
    var viewsVal = carouselRoot.querySelector("[data-carousel-views]");
    var statSep = carouselRoot.querySelector("[data-carousel-stat-sep]");
    var imgA = slides[0];
    var imgB = slides[1];

    if (imgA && imgB && manifestUrl) {
      fetch(manifestUrl)
        .then(function (r) {
          if (!r.ok) throw new Error("manifest " + r.status);
          return r.json();
        })
        .then(function (rawList) {
          if (!Array.isArray(rawList) || rawList.length === 0) throw new Error("empty manifest");
          var entries = rawList
            .map(function (item) {
              return normalizeCarouselEntry(item, thumbDir);
            })
            .filter(Boolean);
          if (entries.length === 0) throw new Error("empty manifest");
          shuffleInPlace(entries);

          var pos = 0;
          var frontIsA = true;

          function applySlide(img, entry) {
            img.src = entry.src;
            img.alt = entry.alt;
          }

          function syncLink(entry) {
            if (!linkEl) return;
            if (entry && entry.href) {
              linkEl.href = entry.href;
              linkEl.hidden = false;
              var name = entry.title || entry.alt.replace(/^Tableau Public thumbnail for\s*/i, "") || "workbook";
              linkEl.setAttribute("aria-label", "Open " + name + " on Tableau Public (opens in new tab)");
            } else {
              linkEl.hidden = true;
              linkEl.removeAttribute("href");
              linkEl.setAttribute("aria-label", "Open workbook on Tableau Public");
            }
          }

          function syncMeta(entry) {
            if (!metaEl || !titleEl) return;
            metaEl.hidden = false;
            var vizName =
              (entry.title && String(entry.title).trim()) ||
              (entry.alt && entry.alt.replace(/^Tableau Public thumbnail for\s*/i, "").trim()) ||
              "Tableau workbook";
            titleEl.textContent = vizName;

            var hasFav = entry.favourites != null;
            var hasViews = entry.views != null;
            if (statsEl && favWrap && viewsWrap && favVal && viewsVal) {
              if (hasFav || hasViews) {
                statsEl.hidden = false;
                favWrap.hidden = !hasFav;
                viewsWrap.hidden = !hasViews;
                if (statSep) statSep.hidden = !(hasFav && hasViews);
                if (hasFav) favVal.textContent = formatStat(entry.favourites);
                if (hasViews) viewsVal.textContent = formatStat(entry.views);
              } else {
                statsEl.hidden = true;
                if (statSep) statSep.hidden = true;
              }
            }
          }

          function syncChrome(entry) {
            syncLink(entry);
            syncMeta(entry);
          }

          function step() {
            pos = (pos + 1) % entries.length;
            var nextEntry = entries[pos];
            var front = frontIsA ? imgA : imgB;
            var back = frontIsA ? imgB : imgA;

            back.onload = function () {
              back.onload = null;
              front.classList.remove("is-visible");
              back.classList.add("is-visible");
              frontIsA = !frontIsA;
              syncChrome(nextEntry);
            };
            applySlide(back, nextEntry);
            if (back.complete && back.naturalWidth) {
              back.onload();
            }
          }

          applySlide(imgA, entries[0]);
          imgA.classList.add("is-visible");
          imgB.classList.remove("is-visible");
          syncChrome(entries[0]);

          if (entries.length > 1) {
            setInterval(step, intervalMs);
          }
        })
        .catch(function () {
          if (fallbackEl) fallbackEl.hidden = false;
        });
    }
  }

  /* Code block copy */
  document.querySelectorAll("[data-code-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wrap = btn.closest(".code-block-wrap");
      if (!wrap) return;
      var pre = wrap.querySelector("pre");
      if (!pre) return;
      var text = pre.textContent || "";

      function fallbackCopy() {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          btn.textContent = "Copied!";
        } catch (e) {
          btn.textContent = "Copy failed";
        }
        document.body.removeChild(ta);
        setTimeout(function () {
          btn.textContent = "Copy";
        }, 2000);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () {
            btn.textContent = "Copied!";
            setTimeout(function () {
              btn.textContent = "Copy";
            }, 2000);
          },
          fallbackCopy
        );
      } else {
        fallbackCopy();
      }
    });
  });
})();
