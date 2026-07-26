/*
 * Galerie "A vendre / a donner".
 *
 * Tout le contenu vient de data/items.json : ce fichier ne contient aucune
 * donnee en dur. Pour ajouter ou retirer un objet, editer data/items.json
 * (voir CLAUDE.md) — il n'y a jamais besoin de toucher a ce script.
 */
(function () {
  "use strict";

  var STATUS = {
    available: { label: null, badge: null, gone: false },
    reserved: { label: "Réservé", badge: "reserved", gone: false },
    sold: { label: "Parti", badge: "gone", gone: true }
  };

  var el = {
    title: document.getElementById("site-title"),
    intro: document.getElementById("site-intro"),
    filters: document.getElementById("filters"),
    hideGone: document.getElementById("hide-gone"),
    gallery: document.getElementById("gallery"),
    count: document.getElementById("count"),
    empty: document.getElementById("empty"),
    contact: document.getElementById("contact-link"),
    contactFooter: document.getElementById("contact-link-footer"),
    lightbox: document.getElementById("lightbox"),
    lbImg: document.getElementById("lb-img"),
    lbLabel: document.getElementById("lb-label"),
    lbContact: document.getElementById("lb-contact"),
    lbClose: document.getElementById("lb-close"),
    lbPrev: document.getElementById("lb-prev"),
    lbNext: document.getElementById("lb-next")
  };

  var data = null;
  var email = "";
  var activeCategory = "all";
  var visible = [];   // objets actuellement affiches, dans l'ordre de la grille
  var lbIndex = -1;
  var lastFocus = null;

  /* ---------- utilitaires ---------- */

  function statusOf(item) {
    return STATUS[item.status] || STATUS.available;
  }

  function isGone(item) {
    return statusOf(item).gone;
  }

  /** Texte affiche pour un objet : son titre si defini, sinon la categorie. */
  function labelOf(item) {
    return item.title || item.categoryLabel;
  }

  function mailto(subject, body) {
    if (!email) return "#";
    var url = "mailto:" + email + "?subject=" + encodeURIComponent(subject);
    if (body) url += "&body=" + encodeURIComponent(body);
    return url;
  }

  /** Identifiant stable utilise dans l'URL (#categorie/photo). */
  function hashOf(item) {
    return item.categoryId + "/" + item.id;
  }

  /* ---------- rendu ---------- */

  function allItems() {
    var out = [];
    data.categories.forEach(function (category) {
      (category.items || []).forEach(function (item) {
        out.push({
          id: item.id,
          status: item.status || "available",
          title: item.title || "",
          note: item.note || "",
          categoryId: category.id,
          categoryLabel: category.label
        });
      });
    });
    return out;
  }

  function renderFilters() {
    var items = allItems();
    var buttons = [{ id: "all", label: "Tout", n: items.length }];

    data.categories.forEach(function (category) {
      buttons.push({
        id: category.id,
        label: category.label,
        n: (category.items || []).length
      });
    });

    el.filters.innerHTML = "";
    buttons.forEach(function (spec) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.setAttribute("aria-pressed", String(spec.id === activeCategory));
      button.dataset.category = spec.id;
      button.innerHTML = '<span></span><span class="n"></span>';
      button.firstChild.textContent = spec.label;
      button.lastChild.textContent = spec.n;
      button.addEventListener("click", function () {
        activeCategory = spec.id;
        renderFilters();
        renderGallery();
      });
      el.filters.appendChild(button);
    });
  }

  function tileFor(item, index) {
    var state = statusOf(item);
    var tile = document.createElement("button");
    tile.type = "button";
    tile.className = "tile";
    if (state.badge === "gone") tile.classList.add("is-gone");
    if (state.badge === "reserved") tile.classList.add("is-reserved");
    tile.dataset.index = String(index);

    var img = document.createElement("img");
    img.src = "images/thumb/" + item.categoryId + "/" + item.id + ".webp";
    img.alt = labelOf(item) + (state.label ? " — " + state.label : "");
    img.setAttribute("loading", "lazy");
    img.setAttribute("decoding", "async");
    tile.appendChild(img);

    if (state.label) {
      var badge = document.createElement("span");
      badge.className = "badge" + (state.badge === "reserved" ? " reserved" : "");
      badge.textContent = state.label;
      tile.appendChild(badge);
    }

    if (item.title) {
      var caption = document.createElement("span");
      caption.className = "tile-label";
      caption.textContent = item.title;
      tile.appendChild(caption);
    }

    tile.addEventListener("click", function () {
      openLightbox(Number(tile.dataset.index));
    });
    return tile;
  }

  function renderGallery() {
    var hideGone = el.hideGone.checked;
    var groups = data.categories.filter(function (category) {
      return activeCategory === "all" || category.id === activeCategory;
    });

    el.gallery.innerHTML = "";
    visible = [];

    groups.forEach(function (category) {
      var items = (category.items || [])
        .map(function (item) {
          return {
            id: item.id,
            status: item.status || "available",
            title: item.title || "",
            note: item.note || "",
            categoryId: category.id,
            categoryLabel: category.label
          };
        })
        .filter(function (item) {
          return !(hideGone && isGone(item));
        });

      if (!items.length) return;

      // Le titre de categorie n'a d'interet que dans la vue "Tout".
      if (activeCategory === "all") {
        var heading = document.createElement("h2");
        heading.className = "cat-title";
        heading.innerHTML = '<span></span> <span class="n"></span>';
        heading.firstChild.textContent = category.label;
        heading.lastChild.textContent = "(" + items.length + ")";
        el.gallery.appendChild(heading);
      }

      var grid = document.createElement("div");
      grid.className = "grid";
      items.forEach(function (item) {
        grid.appendChild(tileFor(item, visible.length));
        visible.push(item);
      });
      el.gallery.appendChild(grid);
    });

    // Un objet reserve n'est plus disponible : seul le statut "available" compte.
    var remaining = visible.filter(function (item) {
      return item.status === "available";
    }).length;
    el.count.textContent =
      remaining === 0
        ? "Aucun objet disponible."
        : remaining + (remaining > 1 ? " objets disponibles" : " objet disponible");
    el.empty.hidden = visible.length > 0;
  }

  /* ---------- visionneuse ---------- */

  function openLightbox(index) {
    if (index < 0 || index >= visible.length) return;
    lastFocus = document.activeElement;
    lbIndex = index;
    showCurrent();
    el.lightbox.hidden = false;
    document.body.style.overflow = "hidden";
    el.lbClose.focus();
  }

  function showCurrent() {
    var item = visible[lbIndex];
    if (!item) return;
    var state = statusOf(item);

    el.lbImg.src = "images/full/" + item.categoryId + "/" + item.id + ".webp";
    el.lbImg.alt = labelOf(item);

    var parts = [labelOf(item)];
    if (state.label) parts.push(state.label);
    if (item.note) parts.push(item.note);
    parts.push((lbIndex + 1) + "/" + visible.length);
    el.lbLabel.textContent = parts.join(" · ");

    el.lbContact.href = mailto(
      "Annonce : " + labelOf(item),
      "Bonjour,\n\nJe suis intéressé(e) par cet objet : " +
        labelOf(item) +
        " (référence " +
        item.id +
        ", " +
        item.categoryLabel +
        ").\n" +
        location.href.split("#")[0] +
        "#" +
        hashOf(item) +
        "\n\n"
    );
    el.lbContact.hidden = state.gone;

    // Permet de partager le lien direct vers une photo.
    history.replaceState(null, "", "#" + hashOf(item));

    // Pré-charge les voisines pour une navigation fluide.
    [lbIndex - 1, lbIndex + 1].forEach(function (i) {
      var neighbour = visible[i];
      if (neighbour) {
        new Image().src =
          "images/full/" + neighbour.categoryId + "/" + neighbour.id + ".webp";
      }
    });
  }

  function closeLightbox() {
    el.lightbox.hidden = true;
    document.body.style.overflow = "";
    history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
    lbIndex = -1;
  }

  function step(delta) {
    if (!visible.length) return;
    lbIndex = (lbIndex + delta + visible.length) % visible.length;
    showCurrent();
  }

  function bindLightbox() {
    el.lbClose.addEventListener("click", closeLightbox);
    el.lbPrev.addEventListener("click", function () { step(-1); });
    el.lbNext.addEventListener("click", function () { step(1); });

    // Un clic sur le fond (et non sur la photo ou les boutons) referme.
    el.lightbox.addEventListener("click", function (event) {
      if (event.target === el.lightbox || event.target.classList.contains("lb-figure")) {
        closeLightbox();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (el.lightbox.hidden) return;
      if (event.key === "Escape") closeLightbox();
      else if (event.key === "ArrowLeft") step(-1);
      else if (event.key === "ArrowRight") step(1);
    });

    // Balayage horizontal sur mobile.
    var startX = 0;
    var startY = 0;
    el.lightbox.addEventListener("touchstart", function (event) {
      startX = event.changedTouches[0].clientX;
      startY = event.changedTouches[0].clientY;
    }, { passive: true });
    el.lightbox.addEventListener("touchend", function (event) {
      var dx = event.changedTouches[0].clientX - startX;
      var dy = event.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
    }, { passive: true });
  }

  /** Ouvre directement la photo ciblee par l'URL (#categorie/photo). */
  function openFromHash() {
    var hash = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (!hash) return;
    for (var i = 0; i < visible.length; i++) {
      if (hashOf(visible[i]) === hash) {
        openLightbox(i);
        return;
      }
    }
  }

  /* ---------- demarrage ---------- */

  function start(payload) {
    data = payload;
    email = (data.contact && data.contact.email) || "";

    if (data.title) {
      el.title.textContent = data.title;
      document.title = data.title;
    }
    el.intro.textContent = data.intro || "";

    var href = mailto(
      "Annonce : " + (data.title || "objets à vendre"),
      "Bonjour,\n\nJe suis intéressé(e) par :\n\n"
    );
    el.contact.href = href;
    el.contactFooter.href = href;
    el.contactFooter.textContent = email || "contact";

    el.hideGone.addEventListener("change", renderGallery);
    bindLightbox();

    renderFilters();
    renderGallery();
    openFromHash();
  }

  fetch("data/items.json", { cache: "no-cache" })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(start)
    .catch(function (error) {
      el.gallery.innerHTML =
        '<p class="empty">Impossible de charger la liste des objets (' +
        error.message +
        ").</p>";
    });
})();
