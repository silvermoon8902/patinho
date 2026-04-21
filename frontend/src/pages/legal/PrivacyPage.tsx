import { Link } from "react-router-dom";

export default function PrivacyPage() {
  return (
    <div className="legal-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-draft">
          Documento em preparação
        </span>
        <h1 className="legal-title">Política de Privacidade</h1>
        <p className="legal-subtitle">
          Como coletamos, usamos e protegemos os seus dados pessoais no Patinho.
        </p>
      </header>

      <section className="legal-summary-card card">
        <h2 className="legal-section-title">Princípios que seguimos</h2>
        <ul className="legal-list">
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">1</span>
            <div>
              <strong>Dados coletados.</strong>
              <p>
                Nome, e-mail, telefone, data de nascimento, CPF (quando
                obrigatório) e o histórico de uso do aplicativo — desafios
                criados, apostas, depósitos e saques.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">2</span>
            <div>
              <strong>Uso.</strong>
              <p>
                Operar a plataforma, processar pagamentos via Pix, prevenir
                fraude e cumprir obrigações legais.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">3</span>
            <div>
              <strong>Compartilhamento.</strong>
              <p>
                Com o Mercado Pago (para processar pagamentos) e autoridades,
                quando legalmente exigido.{" "}
                <strong className="legal-highlight">
                  Nunca vendemos seus dados.
                </strong>
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">4</span>
            <div>
              <strong>Seus direitos.</strong>
              <p>
                Você pode exportar ou excluir seus dados a qualquer momento,
                diretamente no seu perfil.
              </p>
            </div>
          </li>
        </ul>
      </section>

      <section className="legal-cta-card card">
        <div className="legal-cta-content">
          <h3>Quer exercer seus direitos agora?</h3>
          <p>Tudo está disponível no seu perfil.</p>
        </div>
        <Link to="/profile" className="btn btn-primary">
          Ir para o perfil
        </Link>
      </section>

      <footer className="legal-contact card">
        <p className="legal-related">
          Veja também{" "}
          <Link to="/terms" className="legal-link">
            Termos de Uso
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
