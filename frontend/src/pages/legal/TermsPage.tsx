import { Link } from "react-router-dom";

export default function TermsPage() {
  return (
    <div className="legal-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-draft">
          Documento em preparação
        </span>
        <h1 className="legal-title">Termos de Uso</h1>
        <p className="legal-subtitle">
          Estamos finalizando com apoio jurídico. Todos os cadastrados serão
          notificados por e-mail quando o documento definitivo entrar em vigor.
        </p>
      </header>

      <section className="legal-summary-card card">
        <h2 className="legal-section-title">Resumo do que está por vir</h2>
        <ul className="legal-list">
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">1</span>
            <div>
              <strong>Plataforma social entre amigos.</strong>
              <p>
                O Patinho é um espaço de desafios sociais entre pessoas maiores
                de 18 anos — não é uma casa de apostas tradicional.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">2</span>
            <div>
              <strong>Taxa administrativa.</strong>
              <p>
                Cobramos uma taxa sobre o prêmio pago. O valor é sempre exibido
                antes de você confirmar a entrada em um desafio.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">3</span>
            <div>
              <strong>Resolução de disputas.</strong>
              <p>
                Disputas entre participantes são resolvidas pelo sistema interno
                de votação e contestação descrito no aplicativo.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">4</span>
            <div>
              <strong>Território e legislação.</strong>
              <p>
                Uso restrito ao Brasil, sujeito à legislação brasileira.
              </p>
            </div>
          </li>
        </ul>
      </section>

      <footer className="legal-contact card">
        <h3>Dúvidas?</h3>
        <p>
          Fale com a gente em{" "}
          <a href="mailto:contato@patinho.com.br" className="legal-link">
            contato@patinho.com.br
          </a>
        </p>
        <p className="legal-related">
          Veja também{" "}
          <Link to="/privacy" className="legal-link">
            Política de Privacidade
          </Link>{" "}
          ·{" "}
          <Link to="/lgpd" className="legal-link">
            Direitos LGPD
          </Link>
        </p>
      </footer>
    </div>
  );
}
