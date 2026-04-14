import { useState, useEffect, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import patinhoLogo from "@/assets/patinho-logo.png";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const { register, isAuthenticated, loading, error, resetError } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/wallet", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    resetError();
  }, []);

  const validate = (): boolean => {
    setValidationError(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setValidationError("E-mail invalido");
      return false;
    }

    if (username.length < 3) {
      setValidationError("Nome de usuario deve ter pelo menos 3 caracteres");
      return false;
    }

    if (password.length < 8) {
      setValidationError("Senha deve ter pelo menos 8 caracteres");
      return false;
    }

    if (password !== confirmPassword) {
      setValidationError("As senhas nao coincidem");
      return false;
    }

    if (!phone.trim() || phone.trim().length < 8) {
      setValidationError("Telefone e obrigatorio");
      return false;
    }

    if (!birthDate) {
      setValidationError("Data de nascimento e obrigatoria");
      return false;
    }

    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    if (age < 18) {
      setValidationError("Voce precisa ter pelo menos 18 anos");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    await register({
      email,
      username,
      password,
      phone: phone.trim(),
      birth_date: birthDate,
    });
  };

  const displayError = validationError || error;

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <img src={patinhoLogo} alt="Patinho" className="auth-logo-image" />
          <p className="auth-subtitle">Apostas entre Amigos</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Criar conta</h2>

          {displayError && (
            <div className="alert alert-error">{displayError}</div>
          )}

          <div className="form-group">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="username">Nome de usuario</label>
            <input
              id="username"
              type="text"
              placeholder="Escolha um nome"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="phone">Telefone</label>
            <input
              id="phone"
              type="tel"
              placeholder="(11) 99999-9999"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              autoComplete="tel"
            />
          </div>

          <div className="form-group">
            <label htmlFor="birthDate">Data de nascimento</label>
            <input
              id="birthDate"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              required
              max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split("T")[0]}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              placeholder="Minimo 8 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirmar senha</label>
            <input
              id="confirmPassword"
              type="password"
              placeholder="Repita a senha"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
          >
            {loading ? "Criando conta..." : "Criar conta"}
          </button>

          <p className="auth-link">
            Ja tem conta?{" "}
            <Link to="/login">Entrar</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
