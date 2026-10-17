(function () {
  const raiz = document.documentElement;

  try {
    const salvo = localStorage.getItem("tema");
    if (salvo === "claro" || salvo === "escuro") {
      raiz.dataset.tema = salvo;
    }
  } catch (erro) {
    // armazenamento indisponível: segue com o tema padrão
  }

  document.addEventListener("click", (evento) => {
    if (!evento.target.closest("[data-alternar-tema]")) return;

    const novo = raiz.dataset.tema === "claro" ? "escuro" : "claro";
    raiz.dataset.tema = novo;

    try {
      localStorage.setItem("tema", novo);
    } catch (erro) {
      // sem armazenamento, a troca vale só até recarregar
    }
  });
})();