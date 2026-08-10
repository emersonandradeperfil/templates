const NUMERO_WHATSAPP_CLINICA = "5511999999999";

// Atualiza o ano no rodapé automaticamente
document.getElementById("year").textContent = new Date().getFullYear();

// Inicialização do Carrossel 1 (Hero)
const swiperHero = new Swiper('.myDentalSwiper', {
  loop: true,
  effect: 'fade',
  pagination: {
    el: '.myDentalSwiper .swiper-pagination',
    clickable: true,
  },
  autoplay: {
    delay: 5000,
    disableOnInteraction: false,
  },
});

// Inicialização do Carrossel 2 (Depoimentos / Prints do Google)
const swiperReviews = new Swiper('.reviewsSwiper', {
  loop: true,
  slidesPerView: 1,
  spaceBetween: 20,
  pagination: {
    el: '.reviewsSwiper .swiper-pagination',
    clickable: true,
  },
  navigation: {
    nextEl: '.reviewsSwiper .swiper-button-next',
    prevEl: '.reviewsSwiper .swiper-button-prev',
  },
  autoplay: {
    delay: 4000,
    disableOnInteraction: false,
  },
});

// Lógica do Formulário para o WhatsApp
const form = document.getElementById("scheduleForm");
const feedback = document.getElementById("formFeedback");

form.addEventListener("submit", function (event) {
  event.preventDefault();

  const nome = document.getElementById("nome").value.trim();
  const procedimento = document.getElementById("procedimento").value;

  if (!nome || !procedimento) {
    feedback.textContent = "Por favor, preencha todos os campos antes de continuar.";
    feedback.className = "form-feedback error";
    return;
  }

  const mensagem = `Olá! Meu nome é ${nome}, gostaria de agendar uma consulta para o procedimento: ${procedimento}.`;
  const linkWhatsApp = `https://wa.me/${NUMERO_WHATSAPP_CLINICA}?text=${encodeURIComponent(mensagem)}`;

  feedback.textContent = "Tudo certo! Abrindo o WhatsApp...";
  feedback.className = "form-feedback success";

  window.open(linkWhatsApp, "_blank", "noopener");
  form.reset();
});