// --- Copiar para a área de transferência ---
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

// --- Ações sem recarregar a página ---
function mostrarErro(mensagem) {
  const aviso = document.createElement("div");
  aviso.className = "aviso aviso-erro";
  aviso.textContent = mensagem;
  document.querySelector("main").prepend(aviso);
}

document.addEventListener("submit", async (evento) => {
  const formulario = evento.target.closest("form[data-ajax]");
  if (!formulario) return;

  evento.preventDefault();
  const botoes = formulario.querySelectorAll("button, input[type=submit]");
  botoes.forEach((botao) => (botao.disabled = true));

  try {
    const resposta = await fetch(formulario.action, {
      method: "POST",
      body: new FormData(formulario),
    });

    const caminho = new URL(resposta.url).pathname;
    if (resposta.redirected && caminho !== window.location.pathname) {
      window.location.href = resposta.url;
      return;
    }
    if (!resposta.ok) {
      throw new Error(`Resposta ${resposta.status}`);
    }

    const html = await resposta.text();
    const novaPagina = new DOMParser().parseFromString(html, "text/html");
    document.querySelector("main").replaceWith(novaPagina.querySelector("main"));
  } catch (erro) {
    mostrarErro("Não foi possível concluir a ação. Atualize a página e tente de novo.");
    botoes.forEach((botao) => (botao.disabled = false));
  }
});