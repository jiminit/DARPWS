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













