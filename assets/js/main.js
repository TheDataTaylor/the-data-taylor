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

  var carouselRoot = document.querySelector("[data-carousel]");
  if (carouselRoot) {
    var manifestUrl = carouselRoot.getAttribute("data-carousel-manifest") || "";
    var thumbDir = carouselRoot.getAttribute("data-carousel-dir") || "assets/Public Thumbnails";
    var intervalMs = parseInt(carouselRoot.getAttribute("data-carousel-interval") || "5500", 10);
    var slides = carouselRoot.querySelectorAll(".hero-carousel-slide");
    var fallbackEl = carouselRoot.querySelector("[data-carousel-fallback]");
    var imgA = slides[0];
    var imgB = slides[1];

    if (imgA && imgB && manifestUrl) {
      fetch(manifestUrl)
        .then(function (r) {
          if (!r.ok) throw new Error("manifest " + r.status);
          return r.json();
        })
        .then(function (files) {
          if (!Array.isArray(files) || files.length === 0) throw new Error("empty manifest");
          shuffleInPlace(files);

          var pos = 0;
          var frontIsA = true;

          function applySlide(img, file) {
            img.src = thumbnailUrl(thumbDir, file);
            img.alt = altFromFilename(file);
          }

          function step() {
            pos = (pos + 1) % files.length;
            var nextFile = files[pos];
            var front = frontIsA ? imgA : imgB;
            var back = frontIsA ? imgB : imgA;

            back.onload = function () {
              back.onload = null;
              front.classList.remove("is-visible");
              back.classList.add("is-visible");
              frontIsA = !frontIsA;
            };
            applySlide(back, nextFile);
            if (back.complete && back.naturalWidth) {
              back.onload();
            }
          }

          applySlide(imgA, files[0]);
          imgA.classList.add("is-visible");
          imgB.classList.remove("is-visible");

          if (files.length > 1) {
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
