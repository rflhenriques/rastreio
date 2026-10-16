document.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("[data-copiar]");
  if (!botao) return;

  const alvo = document.querySelector(botao.dataset.copiar);
  const textoOriginal = botao.textContent;

  try {
    await navigator.clipboard.writeText(alvo.value);
    botao.textContent = "Copiado!";
  } catch (erro) {
    alvo.select();
    botao.textContent = "Selecione e copie (Ctrl+C)";
  }

  setTimeout(() => {
    botao.textContent = textoOriginal;
  }, 2000);
});