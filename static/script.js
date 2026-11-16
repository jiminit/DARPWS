document.addEventListener("DOMContentLoaded", () => {
  // --- Toggle visibility of nested sections ---
  const diabetesCheck = document.getElementById("diabetesCheck");
  const complicationCheck = document.getElementById("complicationCheck");
  const diabetesOptions = document.getElementById("diabetesOptions");
  const complicationOptions = document.getElementById("complicationOptions");

  function updateVisibility() {
    diabetesOptions.style.display = diabetesCheck.checked ? "block" : "none";
    complicationOptions.style.display = complicationCheck.checked ? "block" : "none";
  }

  diabetesCheck.addEventListener("change", updateVisibility);
  complicationCheck.addEventListener("change", updateVisibility);

  // Nested complication options
  const complicationMap = {
    MIcheck: "MIperc",
    HFcheck: "HFperc",
    STcheck: "STperc",
    PDcheck: "PDperc",
    ESKDcheck: "ESKDperc",
    hypocheck: "hypoperc",
    hypecheck: "hypeperc",
    cvdeathcheck: "cvdeathperc",
    redeathcheck: "redeathperc",
  };

  Object.entries(complicationMap).forEach(([checkId, sectionId]) => {
    const check = document.getElementById(checkId);
    const section = document.getElementById(sectionId);
    check.addEventListener("change", () => {
      section.style.display = check.checked ? "block" : "none";
    });
  });

  const a1ccheck = document.getElementById("a1ccheck");
  const a1csection = document.getElementById("a1csection");
  const compcheck = document.getElementById("compcheck");
  const compsection = document.getElementById("compsection");
  a1ccheck.addEventListener("change", () => {
    a1csection.style.display = a1ccheck.checked ? "block" : "none";
  });
  compcheck.addEventListener("change", () => {
    compsection.style.display = compcheck.checked ? "block" : "none";
  });


  const fixedcheck = document.getElementById("fixedcosts");
  const fixedcostoptions = document.getElementById("fixedcostoptions");
  const annualcheck = document.getElementById("annualcosts");
  const annualcostoptions = document.getElementById("annualcostoptions");
  fixedcheck.addEventListener("change", () => {
    fixedcostoptions.style.display = fixedcheck.checked ? "block" : "none";
  });
  annualcheck.addEventListener("change", () => {
    annualcostoptions.style.display = annualcheck.checked ? "block" : "none";
  });

  const costmap = {
    fixedperPerson: "fixedcostPerPersonInput",
    fixedtotalCost: "fixedtotalCostInput",
    annualperPerson: "annualcostPerPersonInput",
    annualtotalCost: "annualtotalCostInput",
  };

  Object.entries(costmap).forEach(([checkId, sectionId]) => {
    const check = document.getElementById(checkId);
    const section = document.getElementById(sectionId);
    check.addEventListener("change", () => {
      section.style.display = check.checked ? "block" : "none";
    });
  });


  const annualcostTypeRadios = document.querySelectorAll("input[name='annualcostType']");
  const annualcostPerPersonInput = document.getElementById("annualcostPerPersonInput");
  const annualtotalCostInput = document.getElementById("annualtotalCostInput");

  annualcostTypeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      annualcostPerPersonInput.style.display = radio.value === "annualperPerson" ? "block" : "none";
      annualtotalCostInput.style.display = radio.value === "annualtotalCost" ? "block" : "none";
    });
  });


  // --- Toggle cost input sections ---
  const dp_fixedcheck = document.getElementById("dp_fixedcosts");
  const dp_fixedcostoptions = document.getElementById("dp_fixedcostoptions");
  const dp_annualcheck = document.getElementById("dp_annualcosts");
  const dp_annualcostoptions = document.getElementById("dp_annualcostoptions");
  dp_fixedcheck.addEventListener("change", () => {
    dp_fixedcostoptions.style.display = dp_fixedcheck.checked ? "block" : "none";
  });
  dp_annualcheck.addEventListener("change", () => {
    dp_annualcostoptions.style.display = dp_annualcheck.checked ? "block" : "none";
  });


});









(function () {
  // 1. Edit this: one entry per step. `target` is a CSS selector for the "Show me" spotlight.
  const STEPS = [
    {
      title: "What this model does",
      text: "The ALLSPARK model projects the health and economic impacts of interventions to prevent diabetes or its' complications.",
      target: null, example: false
    },
    {
      title: "Select your intervention type",
      text: 'Interventions can either prevent diabetes or its complications. Diabetes prevention interventions call the model described in <a href="https://doi.org/10.1016/j.jval.2023.02.003" target="_blank" rel="noopener noreferrer">Morton et al., 2023</a>;" diabetes complication prevention interventions call the model described in <a href="https://github.com/cardiopharmnerd/ALLSPARK" target="_blank" rel="noopener noreferrer">Livori et al., 2027</a>.',
      target: null, example: false
    },
    {
      title: "Select intervention population and effectiveness",
      text: "Select the age range for the model, and input the effectiveness of your intervention. For diabetes complication prevention, you can choose to model intervention effectiveness via HbA1c reduction and/or direct prevention of complications, but be aware that selecting both may double count (and thus overestimate) the effectiveness of your intervention.",
      target: null, example: false
    },
    {
      title: "Define intervention costs",
      text: "Select which type of costs the model should include. Fixed costs are costs that happen only once, such as an initial start up cost for a new clinic or a once-off screening test; annual costs occur in every year throughout the model, such as ongoing clinicians costs for a clinic or medication costs.",
      target: null, example: false
    },
    {
      title: "Select time horizon and discounting rate",
      text: "The models can run from anywhere between 1 and 20 years and will default to 10 years if nothing is selected. The discounting rate is the rate at which outcomes are diminished in importance over time; 5% discounting is standard in Australia.",
      target: null, example: false
    },
    {
      title: "Estimate cost-effectiveness",
      text: "When you are happy with your model inputs, click 'Estimate cost-effectiveness' to see the results of your intervention.",
      target: null, example: false
    }
  ];
  const SEEN_KEY = "markovGuideSeen", AUTO_OPEN_DELAY = 800;

  const $ = id => document.getElementById(id);
  const drawer = $("guideDrawer"), tab = $("guideTab"), spot = $("guideSpot");
  let idx = 0, visited = new Set();

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }
  };

  function render() {
    const s = STEPS[idx];
    visited.add(idx);
    $("guideProgress").textContent = "Step " + (idx + 1) + " of " + STEPS.length;
    $("guideBar").style.width = ((idx + 1) / STEPS.length * 100) + "%";
    $("guideStep").innerHTML = "<h3></h3><p></p>";
    $("guideStep").firstChild.textContent = s.title;
    $("guideStep").lastChild.innerHTML = s.text;
    $("guideShow").hidden = !s.target;
    $("guideExample").hidden = !s.example;
    $("guidePrev").disabled = idx === 0;
    $("guideNext").textContent = idx === STEPS.length - 1 ? "Finish" : "Next";
    $("guideList").innerHTML = "";
    STEPS.forEach((st, i) => {
      const li = document.createElement("li"), b = document.createElement("button");
      b.textContent = st.title;
      if (i === idx) b.setAttribute("aria-current", "step");
      if (visited.has(i) && i !== idx) b.className = "done";
      b.onclick = () => go(i);
      li.appendChild(b); $("guideList").appendChild(li);
    });
    hideSpot();
  }
  function go(i) { idx = Math.max(0, Math.min(STEPS.length - 1, i)); render(); }

  function open(focus = true) {
    drawer.classList.add("is-open");
    document.body.classList.add("guide-open");
    tab.setAttribute("aria-expanded", "true");
    store.set(SEEN_KEY, "1");
    if (focus) $("guideTitle").focus();
  }
  function close() {
    drawer.classList.remove("is-open");
    document.body.classList.remove("guide-open");
    tab.setAttribute("aria-expanded", "false");
    hideSpot();
    tab.focus();
  }

  /* Spotlight */
  let spotEl = null;
  function placeSpot() {
    if (!spotEl) return;
    const r = spotEl.getBoundingClientRect(), pad = 6;
    Object.assign(spot.style, {
      top: r.top - pad + "px", left: r.left - pad + "px",
      width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px"
    });
  }
  function showSpot() {
    const t = STEPS[idx].target, el = t && document.querySelector(t);
    if (!el) return toast("Couldn't find that part of the page.");
    spotEl = el;
    el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    placeSpot(); spot.classList.add("on");
    setTimeout(placeSpot, 350);          // re-measure after smooth scroll / layout shift
    setTimeout(hideSpot, 3500);
  }
  function hideSpot() { spot.classList.remove("on"); spotEl = null; }
  addEventListener("resize", placeSpot);
  addEventListener("scroll", placeSpot, { passive: true });

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "guide-toast"; t.textContent = msg; t.setAttribute("role", "status");
    document.body.appendChild(t); setTimeout(() => t.remove(), 2500);
  }

  /* Example data: your page implements window.loadExampleData() (or listens for the event) */
  function loadExample() {
    if (typeof window.loadExampleData === "function") window.loadExampleData();
    else document.dispatchEvent(new CustomEvent("guide:load-example"));
    toast("Example data loaded.");
  }

  tab.onclick = () => open();
  $("guideClose").onclick = close;
  $("guideShow").onclick = showSpot;
  $("guideExample").onclick = loadExample;
  $("guidePrev").onclick = () => go(idx - 1);
  $("guideNext").onclick = () => idx === STEPS.length - 1 ? close() : go(idx + 1);
  $("guideRestart").onclick = () => { visited.clear(); go(0); };
  document.addEventListener("keydown", e => { if (e.key === "Escape" && drawer.classList.contains("is-open")) close(); });

  render();
  // Auto-open on first visit only; don't steal focus from the page.
  if (!store.get(SEEN_KEY)) setTimeout(() => open(false), AUTO_OPEN_DELAY);

  // Optional: let other parts of the page open the guide at a step, e.g. an "ⓘ" icon.
  window.openGuide = function (step) { if (typeof step === "number") go(step); open(); };
})();



