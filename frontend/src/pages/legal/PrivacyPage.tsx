export default function PrivacyPage() {
  return (
    <div className="legal-page">
      <h1 className="page-title">Política de Privacidade</h1>
      <div className="card legal-placeholder">
        <p>
          <strong>Documento em preparação.</strong>
        </p>
        <p>
          A Política de Privacidade final está sendo elaborada em conjunto com
          nosso time jurídico. Enquanto isso, aqui estão os princípios que
          seguimos:
        </p>
        <ul>
          <li>
            <strong>Dados coletados.</strong> Nome, e-mail, telefone, data de
            nascimento, CPF (quando obrigatório), e o histórico de uso do
            aplicativo (desafios criados, apostas, depósitos, saques).
          </li>
          <li>
            <strong>Uso.</strong> Operar a plataforma, processar pagamentos
            via Pix, prevenir fraude e cumprir obrigações legais.
          </li>
          <li>
            <strong>Compartilhamento.</strong> Com o Mercado Pago (para
            processar pagamentos) e autoridades, quando legalmente exigido.
            Nunca vendemos seus dados.
          </li>
          <li>
            <strong>Seus direitos.</strong> Você pode exportar ou excluir
            seus dados a qualquer momento em{" "}
            <a href="/profile">seu perfil</a>.
          </li>
        </ul>
        <p>
          Veja também nossa página de{" "}
          <a href="/lgpd">direitos do titular (LGPD)</a>.
        </p>
      </div>
    </div>
  );
}
