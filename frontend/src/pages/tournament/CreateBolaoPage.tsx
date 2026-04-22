import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/store";
import { createTournamentBet } from "@/store/tournamentSlice";
import { useToast } from "@/components/shared/Toast";

const MIN_ENTRY = 5;
const MAX_ENTRY = 1000;
const MIN_PARTICIPANTS = 2;
const MAX_PARTICIPANTS = 500;

export default function CreateBolaoPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [entry, setEntry] = useState("");
  const [maxP, setMaxP] = useState("");
  const [saving, setSaving] = useState(false);

  const entryNum = parseFloat(entry.replace(",", ".")) || 0;
  const maxPNum = parseInt(maxP, 10) || 0;
  const valid =
    entryNum >= MIN_ENTRY &&
    entryNum <= MAX_ENTRY &&
    maxPNum >= MIN_PARTICIPANTS &&
    maxPNum <= MAX_PARTICIPANTS;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) {
      showToast("Verifique o valor de entrada e o máximo de participantes.", "error");
      return;
    }
    setSaving(true);
    try {
      const result = await dispatch(
        createTournamentBet({
          template_code: "bolao_copa_mundo_2026",
          entry_amount: entryNum,
          max_participants: maxPNum,
        })
      );
      if (createTournamentBet.fulfilled.match(result)) {
        showToast("Bolão criado com sucesso!", "success");
        navigate(`/bets/${result.payload.id}`);
      } else {
        showToast((result.payload as string) || "Erro ao criar Bolão", "error");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="create-bet-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-active">
          Template oficial
        </span>
        <h1 className="legal-title">Criar Bolão da Copa do Mundo 2026</h1>
        <p className="legal-subtitle">
          Todos os 48 jogos da fase de grupos ficam disponíveis para palpite
          assim que o participante entrar. Jogos das eliminatórias são
          liberados quando os confrontos forem definidos.
        </p>
      </header>

      <section className="card">
        <h3>Como funciona a pontuação</h3>
        <ul className="legal-list">
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">1</span>
            <div>
              <strong>Fase de grupos.</strong>
              <p>3 pts por acertar o vencedor. 6 pts por acertar o placar exato.</p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">2</span>
            <div>
              <strong>Eliminatórias.</strong>
              <p>6 pts por acertar quem passa. 12 pts por acertar o placar exato.</p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">3</span>
            <div>
              <strong>Campeão da Copa.</strong>
              <p>
                Cada participante escolhe o campeão no momento em que entra
                no bolão. Quem acertar ganha 30 pts de bônus no final.
              </p>
            </div>
          </li>
          <li className="legal-list-item">
            <span className="legal-list-marker" aria-hidden="true">4</span>
            <div>
              <strong>Prêmio final.</strong>
              <p>
                100% do pote (menos a taxa da plataforma) vai para o 1º lugar
                do ranking final. Em caso de empate, divide igual entre os
                líderes empatados.
              </p>
            </div>
          </li>
        </ul>
      </section>

      <form className="card" onSubmit={handleSubmit}>
        <h3>Regras do seu bolão</h3>
        <div className="form-group">
          <label htmlFor="entry">Valor de entrada (por pessoa)</label>
          <div className="input-with-prefix">
            <span className="input-prefix">R$</span>
            <input
              id="entry"
              type="text"
              inputMode="decimal"
              placeholder="50,00"
              value={entry}
              onChange={(e) => {
                const v = e.target.value
                  .replace(",", ".")
                  .replace(/[^0-9.]/g, "");
                setEntry(v);
              }}
            />
          </div>
          <span className="form-hint">
            Entre R$ {MIN_ENTRY},00 e R$ {MAX_ENTRY.toLocaleString("pt-BR")},00.
            Todos os participantes entram com o mesmo valor.
          </span>
        </div>
        <div className="form-group">
          <label htmlFor="maxP">Máximo de participantes</label>
          <input
            id="maxP"
            type="text"
            inputMode="numeric"
            placeholder="Ex: 50"
            value={maxP}
            onChange={(e) => setMaxP(e.target.value.replace(/[^0-9]/g, ""))}
          />
          <span className="form-hint">
            Entre {MIN_PARTICIPANTS} e {MAX_PARTICIPANTS} participantes.
          </span>
        </div>
        <button
          type="submit"
          className="btn btn-primary btn-full"
          disabled={saving || !valid}
        >
          {saving ? "Criando..." : "Criar bolão"}
        </button>
      </form>
    </div>
  );
}
