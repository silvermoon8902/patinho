import { useState, useEffect, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import patinhoLogo from "@/assets/patinho-logo.png";
import patinhoLogoWhite from "@/assets/patinho-logo-white.png";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [birthDay, setBirthDay] = useState("");
  const [birthMonth, setBirthMonth] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const { register, isAuthenticated, loading, error, resetError } = useAuth();
  const { theme } = useTheme();
  const logoSrc = theme === "dark" ? patinhoLogoWhite : patinhoLogo;
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

    if (!birthDay || !birthMonth || !birthYear) {
      setValidationError("Data de nascimento e obrigatoria");
      return false;
    }

    const today = new Date();
    const y = parseInt(birthYear);
    const m = parseInt(birthMonth);
    const d = parseInt(birthDay);
    let age = today.getFullYear() - y;
    if (today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d)) age--;
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
      birth_date: `${birthYear}-${birthMonth.padStart(2, "0")}-${birthDay.padStart(2, "0")}`,
    });
  };

  const displayError = validationError || error;

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <img src={logoSrc} alt="Patinho" className="auth-logo-image" />
          <p className="auth-subtitle">Desafios entre Amigos</p>
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
            <label>Data de nascimento</label>
            <div className="birth-date-row">
              <select
                value={birthDay}
                onChange={(e) => setBirthDay(e.target.value)}
                required
              >
                <option value="">Dia</option>
                {Array.from({ length: 31 }, (_, i) => (
                  <option key={i + 1} value={String(i + 1)}>{String(i + 1).padStart(2, "0")}</option>
                ))}
              </select>
              <select
                value={birthMonth}
                onChange={(e) => setBirthMonth(e.target.value)}
                required
              >
                <option value="">Mes</option>
                {["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"].map((m, i) => (
                  <option key={i + 1} value={String(i + 1)}>{m}</option>
                ))}
              </select>
              <select
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value)}
                required
              >
                <option value="">Ano</option>
                {Array.from({ length: 80 }, (_, i) => {
                  const y = new Date().getFullYear() - 18 - i;
                  return <option key={y} value={String(y)}>{y}</option>;
                })}
              </select>
            </div>
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
