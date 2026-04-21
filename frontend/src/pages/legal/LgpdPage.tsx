export default function LgpdPage() {
  return (
    <div className="legal-page">
      <h1 className="page-title">Seus direitos (LGPD)</h1>
      <div className="card legal-placeholder">
        <p>
          A Lei Geral de Proteção de Dados (Lei nº 13.709/2018) garante a você
          os seguintes direitos sobre os seus dados pessoais. Para exercer
          qualquer deles, acesse o seu <a href="/profile">perfil</a> ou
          entre em contato:
        </p>
        <ul>
          <li>
            <strong>Acesso / portabilidade.</strong> Você pode baixar uma
            cópia de todos os seus dados pelo botão "Exportar meus dados" no
            perfil.
          </li>
          <li>
            <strong>Correção.</strong> Atualize nome de usuário e telefone a
            qualquer momento no perfil.
          </li>
          <li>
            <strong>Exclusão / anonimização.</strong> Use o botão "Excluir
            minha conta" no perfil. Seus dados pessoais serão apagados;
            registros de apostas permanecem anonimizados para fins de auditoria.
          </li>
          <li>
            <strong>Retirada de consentimento.</strong> A exclusão da conta
            revoga todos os consentimentos concedidos.
          </li>
          <li>
            <strong>Informações sobre tratamento.</strong> Veja nossa{" "}
            <a href="/privacy">Política de Privacidade</a>.
          </li>
        </ul>
        <p>
          <strong>Encarregado pelo Tratamento de Dados (DPO):</strong>{" "}
          <a href="mailto:dpo@patinho.com.br">dpo@patinho.com.br</a>
        </p>
        <p className="form-hint">
          Documento completo em preparação. O mecanismo para exercer estes
          direitos já está disponível no seu perfil.
        </p>
      </div>
    </div>
  );
}
