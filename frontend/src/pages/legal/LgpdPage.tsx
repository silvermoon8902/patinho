import { Link } from "react-router-dom";

export default function LgpdPage() {
  return (
    <div className="legal-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-active">
          Mecanismo disponível no perfil
        </span>
        <h1 className="legal-title">Seus direitos (LGPD)</h1>
        <p className="legal-subtitle">
          A Lei Geral de Proteção de Dados (Lei nº 13.709/2018) garante a você
          estes direitos sobre os seus dados pessoais.
        </p>
      </header>

      <section className="legal-rights-grid">
        <article className="legal-right-card card">
          <div className="legal-right-header">
            <span className="legal-right-tag">Direito 1</span>
            <h3>Acesso e portabilidade</h3>
          </div>
          <p>
            Baixe uma cópia completa de todos os seus dados em formato JSON, a
            qualquer momento.
          </p>
          <Link to="/profile" className="legal-right-action">
            Exportar meus dados →
          </Link>
        </article>

        <article className="legal-right-card card">
          <div className="legal-right-header">
            <span className="legal-right-tag">Direito 2</span>
            <h3>Correção</h3>
          </div>
          <p>
            Atualize seu nome de usuário, telefone e outros dados cadastrais
            sempre que precisar.
          </p>
          <Link to="/profile" className="legal-right-action">
            Editar perfil →
          </Link>
        </article>

        <article className="legal-right-card card">
          <div className="legal-right-header">
            <span className="legal-right-tag">Direito 3</span>
            <h3>Exclusão e anonimização</h3>
          </div>
          <p>
            Apague seus dados pessoais. Registros históricos de apostas são
            mantidos anonimizados apenas para fins de auditoria.
          </p>
          <Link to="/profile" className="legal-right-action">
            Excluir minha conta →
          </Link>
        </article>

        <article className="legal-right-card card">
          <div className="legal-right-header">
            <span className="legal-right-tag">Direito 4</span>
            <h3>Retirada de consentimento</h3>
          </div>
          <p>
            A exclusão da conta revoga automaticamente todos os consentimentos
            concedidos previamente.
          </p>
        </article>

        <article className="legal-right-card card">
          <div className="legal-right-header">
            <span className="legal-right-tag">Direito 5</span>
            <h3>Informações sobre tratamento</h3>
          </div>
          <p>
            Consulte como tratamos seus dados na nossa Política de Privacidade.
          </p>
          <Link to="/privacy" className="legal-right-action">
            Ver política →
          </Link>
        </article>
      </section>

      <section className="legal-cta-card card">
        <div className="legal-cta-content">
          <h3>Encarregado pelo Tratamento de Dados (DPO)</h3>
          <p>
            Dúvidas sobre o tratamento dos seus dados ou dificuldade para
            exercer algum direito?
          </p>
          <a href="mailto:dpo@patinho.com.br" className="legal-link">
            dpo@patinho.com.br
          </a>
        </div>
      </section>

      <p className="legal-footnote">
        O documento completo da nossa política de privacidade está em
        preparação. Enquanto isso, os mecanismos para exercer todos estes
        direitos já estão ativos e disponíveis.
      </p>
    </div>
  );
}
