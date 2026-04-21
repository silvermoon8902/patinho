export default function TermsPage() {
  return (
    <div className="legal-page">
      <h1 className="page-title">Termos de Uso</h1>
      <div className="card legal-placeholder">
        <p>
          <strong>Documento em preparação.</strong>
        </p>
        <p>
          Estamos finalizando nossos Termos de Uso com apoio jurídico. Assim
          que o documento estiver pronto, ele será publicado aqui e todos os
          usuários cadastrados serão notificados por e-mail.
        </p>
        <p>
          Em resumo, o Patinho:
        </p>
        <ul>
          <li>
            É uma plataforma de desafios sociais entre amigos maiores de 18
            anos.
          </li>
          <li>
            Cobra uma taxa administrativa sobre os prêmios pagos (exibida
            antes de cada aposta).
          </li>
          <li>
            Não é responsável por disputas entre participantes além do sistema
            interno de votação e contestação.
          </li>
          <li>
            Pode ser usado apenas dentro do Brasil e está sujeito à legislação
            brasileira.
          </li>
        </ul>
        <p className="form-hint">
          Dúvidas?{" "}
          <a href="mailto:contato@patinho.com.br">contato@patinho.com.br</a>
        </p>
      </div>
    </div>
  );
}
