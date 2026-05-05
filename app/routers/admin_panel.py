"""Pannello amministrativo per gestione torneo.

Interfaccia HTML + endpoint per admin:
- Aggiungere/eliminare squadre (partecipanti = squadre)
- Inserire risultati partite con calcolo automatico punti
- Punti distribuiti automaticamente ai team owner
- Visualizzare elenco squadre e team

Protezione: richiede header X-Admin-Token valido.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from ..database import get_supabase_client

router = APIRouter(tags=["Admin"], include_in_schema=False)


def verify_admin_token(token: str = None) -> bool:
	"""Verifica token admin da header X-Admin-Token."""
	return token == "a3f9c4b8de"


@router.get("/admin", response_class=HTMLResponse)
def serve_admin_panel():
	"""Pagina HTML interattiva per amministratori torneo."""

	html = """
<!DOCTYPE html>
<html lang="it">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Admin - FDC Fantatorneo</title>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
			background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
			color: #e5e7eb;
			min-height: 100vh;
			padding: 20px;
		}
		.container { max-width: 1800px; margin: 0 auto; }
		.header {
			background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
			color: white;
			padding: 30px;
			border-radius: 12px;
			margin-bottom: 30px;
			display: flex;
			justify-content: space-between;
			align-items: center;
		}
		.header h1 { font-size: 2em; }
		.auth-section { background: rgba(0,0,0,0.3); padding: 15px 20px; border-radius: 8px; display: flex; gap: 10px; align-items: center; }
		.auth-section input { padding: 8px 12px; border: 1px solid #4b5563; background: #1f2937; color: white; border-radius: 4px; }
		.auth-section button { padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
		.auth-section button:hover { background: #059669; }
		.auth-status { padding: 8px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; display: none; }
		.auth-status.success { background: #d1fae5; color: #065f46; display: block; }
		.auth-status.error { background: #fee2e2; color: #991b1b; display: block; }

		.content { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
		.panel { background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 25px; }
		.panel h2 { color: #7c3aed; margin-bottom: 20px; font-size: 1.5em; }
		.form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
		.form-group label { font-size: 13px; font-weight: 600; color: #9ca3af; margin-bottom: 5px; }
		.form-group input, .form-group select { padding: 10px 12px; border: 1px solid #374151; background: #111827; color: #e5e7eb; border-radius: 6px; font-size: 13px; }
		.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; width: 100%; }
		.btn-primary { background: #7c3aed; color: white; }
		.btn-primary:hover { background: #6d28d9; }
		.btn-danger { background: #ef4444; color: white; }
		.btn-danger:hover { background: #dc2626; }
		.status { margin-top: 15px; padding: 12px; border-radius: 6px; font-size: 13px; display: none; }
		.status.success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; display: block; }
		.status.error { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; display: block; }

		table { width: 100%; border-collapse: collapse; margin-top: 15px; }
		thead { background: rgba(124, 58, 237, 0.1); }
		th { padding: 12px; text-align: left; font-weight: 600; font-size: 12px; color: #7c3aed; text-transform: uppercase; border-bottom: 1px solid #374151; }
		td { padding: 12px; border-bottom: 1px solid #374151; font-size: 13px; }
		tr:hover { background: rgba(124, 58, 237, 0.05); }

		.admin-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
		.admin-table th { background: rgba(124, 58, 237, 0.2); }
		.admin-table input {
			width: 100%;
			padding: 6px 8px;
			border: 1px solid #374151;
			background: #0f172a;
			color: #e5e7eb;
			border-radius: 6px;
			font-size: 12px;
		}
		.admin-table input:focus { outline: none; border-color: #7c3aed; }
		.btn-save {
			background: #10b981;
			color: white;
			border: none;
			border-radius: 6px;
			padding: 6px 12px;
			font-size: 12px;
			font-weight: 600;
			cursor: pointer;
		}
		.btn-save:hover { background: #059669; }

		.full-width { grid-column: 1 / -1; }
		@media (max-width: 1200px) {
			.content { grid-template-columns: 1fr; }
		}
	</style>
</head>
<body>
	<div class="container">
		<div class="header">
			<div>
				<h1>⚙️ Admin Panel - FDC Fantatorneo</h1>
				<p>Gestione squadre, partite, punti automatici</p>
			</div>
			<div class="auth-section">
				<label style="color: white; font-size: 12px;">Token:</label>
				<input type="password" id="adminToken" />
				<button onclick="authenticateAdmin()">Accedi</button>
				<div id="authStatus" class="auth-status"></div>
			</div>
		</div>

		<div id="adminContent" style="display: none;">
			<div class="content">
				<div class="panel">
					<h2>➕ Nuova Squadra</h2>
					<form onsubmit="addSquad(event)">
						<div class="form-group">
							<label>Nome Squadra</label>
							<input type="text" id="squadName" required>
						</div>
						<div class="form-group">
							<label>Sport</label>
							<select id="squadSport" required onchange="updateCost()">
								<option value="">Seleziona sport</option>
								<option value="Calcio">Calcio (35 DomeCoin)</option>
								<option value="Pallavolo">Pallavolo (25 DomeCoin)</option>
								<option value="Padel">Padel (20 DomeCoin)</option>
							</select>
						</div>
						<div class="form-group">
							<label>Costo (auto)</label>
							<input type="number" id="squadCost" readonly>
						</div>
						<div class="form-group">
							<label>Composto da (giocatori, es: Ronaldo, Messi)</label>
							<input type="text" id="squadComposedOf" placeholder="Nomi separati da virgola...">
						</div>
						<button type="submit" class="btn btn-primary">Crea Squadra</button>
						<div id="addSquadStatus" class="status"></div>
					</form>
				</div>

				<div class="panel">
					<h2>🏟️ Nuova Partita</h2>
					<form onsubmit="recordMatch(event)">
						<div class="form-group">
							<label>Squadra Home</label>
							<select id="homeSquad" required>
								<option value="">Seleziona squadra</option>
							</select>
						</div>
						<div class="form-group">
							<label>Squadra Away</label>
							<select id="awaySquad" required>
								<option value="">Seleziona squadra</option>
							</select>
						</div>
						<div class="form-group">
							<label>Fase</label>
							<select id="matchStage" required>
								<option value="group">Girone</option>
								<option value="final">Finale</option>
							</select>
						</div>
						<div class="form-group">
							<label>Risultato Home</label>
							<input type="number" id="homeScore" min="0" required>
						</div>
						<div class="form-group">
							<label>Risultato Away</label>
							<input type="number" id="awayScore" min="0" required>
						</div>
						<button type="submit" class="btn btn-primary">Registra Partita</button>
						<div id="matchStatus" class="status"></div>
					</form>
				</div>

				<div class="panel">
					<h2>🗑️ Elimina Squadra</h2>
					<form onsubmit="deleteSquadHandler(event)">
						<div class="form-group">
							<label>Squadra</label>
							<select id="deleteSquadSelect" required>
								<option value="">Seleziona squadra</option>
							</select>
						</div>
						<p style="font-size: 12px; color: #f87171; margin-bottom: 15px;">⚠️ Azione irreversibile!</p>
						<button type="submit" class="btn btn-danger">Elimina</button>
						<div id="deleteStatus" class="status"></div>
					</form>
				</div>

				<div class="panel">
					<h2>⭐ Assegna Punti</h2>
					<form onsubmit="assignPoints(event)">
						<div class="form-group">
							<label>Squadra</label>
							<select id="pointsSquad" required>
								<option value="">Seleziona squadra</option>
							</select>
						</div>
						<div class="form-group">
							<label>Punti da Aggiungere</label>
							<input type="number" id="pointsAmount" required>
						</div>
						<button type="submit" class="btn btn-primary">Assegna Punti</button>
						<div id="pointsStatus" class="status"></div>
					</form>
				</div>

				<div class="panel">
					<h2>➖ Rimuovi Punti</h2>
					<form onsubmit="removePoints(event)">
						<div class="form-group">
							<label>Squadra</label>
							<select id="removePointsSquad" required>
								<option value="">Seleziona squadra</option>
							</select>
						</div>
						<div class="form-group">
							<label>Punti da Rimuovere</label>
							<input type="number" id="removePointsAmount" min="1" required>
						</div>
						<button type="submit" class="btn btn-danger">Rimuovi Punti</button>
						<div id="removePointsStatus" class="status"></div>
					</form>
				</div>
			</div>

			<div class="panel full-width">
				<h2>📋 Squadre</h2>
				<div style="overflow-x: auto;">
					<table>
						<thead>
							<tr>
								<th>ID</th>
								<th>Nome</th>
								<th>Sport</th>
								<th>Costo</th>
								<th>Punti</th>
							</tr>
						</thead>
						<tbody id="squadsTable">
							<tr><td colspan="5" style="text-align: center; color: #9ca3af;">Caricamento...</td></tr>
						</tbody>
					</table>
				</div>
			</div>

			<div class="panel full-width">
				<h2>👥 Team Giocatori</h2>
				<div style="overflow-x: auto;">
					<table>
						<thead>
							<tr>
								<th>ID</th>
								<th>Nome</th>
								<th>Score</th>
								<th>Costo Totale</th>
								<th>Crediti</th>
							</tr>
						</thead>
						<tbody id="teamsTable">
							<tr><td colspan="5" style="text-align: center; color: #9ca3af;">Caricamento...</td></tr>
						</tbody>
					</table>
				</div>
			</div>

			<div class="panel full-width">
				<h2>✏️ Modifica Classifiche</h2>
				<p style="color: #9ca3af; font-size: 13px; margin-bottom: 15px;">
					Aggiorna PF, V, S, GF/GS o SV/SP e punteggi. Richiede token admin.
				</p>
				<div style="margin-bottom: 20px;">
					<h3 style="margin-bottom: 10px;">🏆 Partecipanti (Squadre)</h3>
					<div id="adminParticipantsContainer">
						Caricamento...
					</div>
				</div>
				<div>
					<h3 style="margin-bottom: 10px;">👥 Team Gestori</h3>
					<div id="adminTeamsContainer">
						Caricamento...
					</div>
				</div>
			</div>

			<div class="panel full-width">
				<h2>🏐 Pallavolo - Gironi e Finali</h2>
				<div id="volleyStructureContainer">
					Caricamento...
				</div>
			</div>
		</div>
	</div>

	<script>
		const API_BASE = 'http://localhost:8000/api/v1';
		const ADMIN_TOKEN_STORAGE_KEY = 'fdc_admin_token';
		let adminToken = null;
		let lastSquads = [];
		const sportCosts = { 'Calcio': 35, 'Pallavolo': 25, 'Padel': 20 };

		function getAdminToken() {
			return adminToken || localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
		}

		function saveAdminToken(token) {
			adminToken = token;
			localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
		}

		function initAdminToken() {
			const storedToken = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
			if (storedToken) {
				adminToken = storedToken;
				const tokenInput = document.getElementById('adminToken');
				tokenInput.value = storedToken;
				tokenInput.disabled = true;
				document.getElementById('adminContent').style.display = 'block';
				showAuthStatus('✓ Token admin caricato', 'success');
				loadSquads();
				loadTeams();
				loadAdminData();
				loadVolleyStructure();
			}
		}

		function authenticateAdmin() {
			const tokenValue = document.getElementById('adminToken').value;
			if (!tokenValue) {
				showAuthStatus('Inserisci token', 'error');
				return;
			}

			if (tokenValue === 'a3f9c4b8de') {
				saveAdminToken(tokenValue);
				showAuthStatus('✓ Autenticazione riuscita', 'success');
				document.getElementById('adminContent').style.display = 'block';
				document.getElementById('adminToken').disabled = true;
				loadSquads();
				loadTeams();
				loadAdminData();
				loadVolleyStructure();
			} else {
				showAuthStatus('✗ Token non valido', 'error');
			}
		}

		function showAuthStatus(msg, type) {
			const el = document.getElementById('authStatus');
			el.textContent = msg;
			el.className = 'auth-status ' + type;
		}

		function showStatus(id, msg, type) {
			const el = document.getElementById(id);
			el.textContent = msg;
			el.className = 'status ' + type;
		}

		async function readResponseMessage(response) {
			const contentType = response.headers.get('content-type') || '';
			if (contentType.includes('application/json')) {
				try {
					const payload = await response.json();
					return payload.detail || payload.message || JSON.stringify(payload);
				} catch (error) {
					return 'Errore non valido';
				}
			}

			try {
				const text = await response.text();
				return text || 'Errore non valido';
			} catch (error) {
				return 'Errore non valido';
			}
		}

		function updateCost() {
			const sport = document.getElementById('squadSport').value;
			const cost = sportCosts[sport] || 0;
			document.getElementById('squadCost').value = cost;
		}

		async function loadAdminData() {
			try {
				const [rankingRes, teamsRes] = await Promise.all([
					fetch(`${API_BASE}/market/ranking`),
					fetch(`${API_BASE}/teams`)
				]);

				const ranking = rankingRes.ok ? await rankingRes.json() : [];
				const teams = teamsRes.ok ? await teamsRes.json() : [];

				renderAdminParticipantsTable(ranking);
				renderAdminTeamsTable(teams);
			} catch (err) {
				console.error('Errore caricamento admin:', err);
				document.getElementById('adminParticipantsContainer').innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
				document.getElementById('adminTeamsContainer').innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
			}
		}

		async function loadVolleyStructure() {
			const container = document.getElementById('volleyStructureContainer');
			if (!container) return;
			try {
				const response = await fetch(`${API_BASE}/market/volley/structure`);
				const payload = response.ok ? await response.json() : null;
				if (!response.ok || !payload) {
					container.innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
					return;
				}
				container.innerHTML = renderVolleyStructure(payload);
			} catch (err) {
				container.innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
			}
		}

		function renderVolleyStructure(data) {
			const groupA = (data.groups && data.groups.A) || [];
			const groupB = (data.groups && data.groups.B) || [];
			const finals = data.finals || {};

			const renderGroupTable = (title, teams) => {
				const rows = teams.length
					? teams.map((team, index) => `
						<tr>
							<td>${index + 1}</td>
							<td>${team.name || 'Squadra ' + team.id}</td>
							<td>${team.matches_played || 0}</td>
							<td>${team.wins || 0}</td>
							<td>${team.losses || 0}</td>
							<td>${team.sets_won || 0}</td>
							<td>${team.sets_lost || 0}</td>
							<td>${team.points || 0}</td>
						</tr>
					`).join('')
					: '<tr><td colspan="8" style="text-align:center; color:#9ca3af;">Nessuna squadra</td></tr>';
				return `
					<h3 style="margin: 10px 0;">${title}</h3>
					<table class="admin-table">
						<thead>
							<tr>
								<th>Pos</th>
								<th>Squadra</th>
								<th>PF</th>
								<th>V</th>
								<th>S</th>
								<th>SV</th>
								<th>SP</th>
								<th>Pti</th>
							</tr>
						</thead>
						<tbody>
							${rows}
						</tbody>
					</table>
				`;
			};

			const formatTeamName = (team) => team ? (team.name || ('Squadra ' + team.id)) : '-';
			const formatScore = (pair) => {
				if (!pair || !pair.match || !pair.home || !pair.away) return '-';
				const match = pair.match;
				const homeScore = match.home_score ?? 0;
				const awayScore = match.away_score ?? 0;
				return match.home_squad_id === pair.home.id
					? `${homeScore}-${awayScore}`
					: `${awayScore}-${homeScore}`;
			};

			const renderFinalRow = (label, pair) => `
				<tr>
					<td>${label}</td>
					<td>${formatTeamName(pair.home)}</td>
					<td>${formatTeamName(pair.away)}</td>
					<td>${formatScore(pair)}</td>
				</tr>
			`;

			return `
				${renderGroupTable('Girone A', groupA)}
				${renderGroupTable('Girone B', groupB)}
				<h3 style="margin: 20px 0 10px;">Finali</h3>
				<table class="admin-table">
					<thead>
						<tr>
							<th>Fase</th>
							<th>Squadra</th>
							<th>Squadra</th>
							<th>Risultato</th>
						</tr>
					</thead>
					<tbody>
						${renderFinalRow('Finale 5/6', finals.fifth_sixth || {})}
						${renderFinalRow('Finale 3/4', finals.third_fourth || {})}
						${renderFinalRow('Finale 1/2', finals.final || {})}
					</tbody>
				</table>
			`;
		}

		function renderAdminParticipantsTable(participants) {
			const isCalcio = (item) => (item.sport || item.role || '').toLowerCase() === 'calcio';
			let html = `
				<table class="admin-table">
					<thead>
						<tr>
							<th>ID</th>
							<th>Nome</th>
							<th>Sport</th>
							<th>Gir</th>
							<th>PF</th>
							<th>V</th>
							<th>S</th>
							<th>GF/SV</th>
							<th>GS/SP</th>
							<th>Pti</th>
							<th>Azione</th>
						</tr>
					</thead>
					<tbody>
			`;

			participants.forEach(p => {
				const sport = p.sport || p.role || 'N/A';
				const isCal = sport.toLowerCase() === 'calcio';
				const isVolley = sport.toLowerCase() === 'pallavolo';
				const gf = isCal ? (p.goals_for || 0) : (p.sets_won || 0);
				const gs = isCal ? (p.goals_against || 0) : (p.sets_lost || 0);
				const groupValue = (p.group_code || '').toUpperCase();
				const groupCell = isVolley
					? `<select id="group_${p.id}">
						<option value="" ${groupValue === '' ? 'selected' : ''}></option>
						<option value="A" ${groupValue === 'A' ? 'selected' : ''}>A</option>
						<option value="B" ${groupValue === 'B' ? 'selected' : ''}>B</option>
					</select>`
					: '<span>-</span>';
				const composedOfDisplay = (p.composed_of || '').substring(0, 30) + ((p.composed_of && p.composed_of.length > 30) ? '...' : '');
				html += `
					<tr>
						<td>${p.id}</td>
						<td>${p.name || 'N/A'}</td>
						<td>${sport}</td>
						<td>${groupCell}</td>
						<td><input type="number" value="${p.matches_played || 0}" id="pg_${p.id}" min="0"></td>
						<td><input type="number" value="${p.wins || 0}" id="wins_${p.id}" min="0"></td>
						<td><input type="number" value="${p.losses || 0}" id="losses_${p.id}" min="0"></td>
						<td><input type="number" value="${gf}" id="gf_${p.id}" min="0"></td>
						<td><input type="number" value="${gs}" id="gs_${p.id}" min="0"></td>
						<td><input type="number" value="${p.points || p.score || 0}" id="points_${p.id}" min="0"></td>
						<td><input type="text" value="${(p.composed_of || '').replace(/"/g, '&quot;')}" id="composed_${p.id}" placeholder="Es: Ronaldo, Messi..."></td>
						<td><button class="btn-save" onclick="saveParticipantChanges(${p.id}, '${sport}')">Salva</button></td>
					</tr>
				`;
			});

			html += `</tbody></table>`;
			document.getElementById('adminParticipantsContainer').innerHTML = html;
		}

		function renderAdminTeamsTable(teams) {
			let html = `
				<table class="admin-table">
					<thead>
						<tr>
							<th>ID</th>
							<th>Nome Team</th>
							<th>Punteggio</th>
							<th>Crediti</th>
							<th>Azione</th>
						</tr>
					</thead>
					<tbody>
			`;

			teams.forEach(t => {
				html += `
					<tr>
						<td>${t.id}</td>
						<td>${t.name || 'Team ' + t.id}</td>
						<td><input type="number" value="${t.score || 0}" id="team_score_${t.id}" min="0"></td>
						<td><input type="number" value="${t.balance_credits || 0}" id="team_credits_${t.id}" min="0"></td>
						<td><button class="btn-save" onclick="saveTeamChanges(${t.id})">Salva</button></td>
					</tr>
				`;
			});

			html += `</tbody></table>`;
			document.getElementById('adminTeamsContainer').innerHTML = html;
		}

		async function saveParticipantChanges(participantId, sport) {
			const token = getAdminToken();
			if (!token) {
				alert('✗ Admin token required');
				return;
			}

			const pg = parseInt(document.getElementById(`pg_${participantId}`).value) || 0;
			const wins = parseInt(document.getElementById(`wins_${participantId}`).value) || 0;
			const losses = parseInt(document.getElementById(`losses_${participantId}`).value) || 0;
			const gf = parseInt(document.getElementById(`gf_${participantId}`).value) || 0;
			const gs = parseInt(document.getElementById(`gs_${participantId}`).value) || 0;
			const points = parseInt(document.getElementById(`points_${participantId}`).value) || 0;
			const composedOf = document.getElementById(`composed_${participantId}`).value || null;

			const isCal = sport.toLowerCase() === 'calcio';
			const isVolley = sport.toLowerCase() === 'pallavolo';
			const payload = {
				score: points,
				wins: wins,
				losses: losses,
				composed_of: composedOf
			};

			if (isVolley) {
				const groupEl = document.getElementById(`group_${participantId}`);
				payload.group_code = groupEl ? groupEl.value : '';
			}

			if (isCal) {
				payload.matches_played = pg;
				payload.goals_for = gf;
				payload.goals_against = gs;
			} else if (sport.toLowerCase() !== 'pallavolo') {
				payload.matches_played = pg;
				payload.sets_won = gf;
				payload.sets_lost = gs;
			}

			try {
				const response = await fetch(`${API_BASE}/market/admin/participants/${participantId}`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-Admin-Token': token
					},
					body: JSON.stringify(payload)
				});

				if (response.ok) {
					alert(`✓ Partecipante ${participantId} aggiornato`);
				} else {
					const err = await response.json();
					alert(`✗ Errore: ${err.detail || 'Aggiornamento fallito'}`);
				}
			} catch (err) {
				alert(`✗ Errore: ${err.message}`);
			}
		}

		async function saveTeamChanges(teamId) {
			const token = getAdminToken();
			if (!token) {
				alert('✗ Admin token required');
				return;
			}

			const score = parseInt(document.getElementById(`team_score_${teamId}`).value) || 0;
			const credits = parseInt(document.getElementById(`team_credits_${teamId}`).value) || 0;

			try {
				const response = await fetch(`${API_BASE}/market/admin/teams/${teamId}`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-Admin-Token': token
					},
					body: JSON.stringify({
						score: score,
						balance_credits: credits
					})
				});

				if (response.ok) {
					alert(`✓ Team ${teamId} aggiornato`);
				} else {
					const err = await response.json();
					alert(`✗ Errore: ${err.detail || 'Aggiornamento fallito'}`);
				}
			} catch (err) {
				alert(`✗ Errore: ${err.message}`);
			}
		}

		async function addSquad(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('addSquadStatus', '✗ Admin token required', 'error');
				return;
			}

			const payload = {
				name: document.getElementById('squadName').value,
				role: document.getElementById('squadSport').value,
				cost: parseInt(document.getElementById('squadCost').value),
				composed_of: document.getElementById('squadComposedOf').value || null
			};

			try {
				const res = await fetch(`${API_BASE}/participants`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify(payload)
				});

				if (res.ok) {
					showStatus('addSquadStatus', '✓ Squadra creata', 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('addSquadStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('addSquadStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function recordMatch(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('matchStatus', '✗ Admin token required', 'error');
				return;
			}

			const homeId = parseInt(document.getElementById('homeSquad').value);
			const awayId = parseInt(document.getElementById('awaySquad').value);
			const stage = document.getElementById('matchStage').value || 'group';

			if (homeId === awayId) {
				showStatus('matchStatus', '✗ Seleziona squadre diverse', 'error');
				return;
			}

			try {
				const res = await fetch(`${API_BASE}/market/match`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({
						home_squad_id: homeId,
						away_squad_id: awayId,
						home_score: parseInt(document.getElementById('homeScore').value),
						away_score: parseInt(document.getElementById('awayScore').value),
						stage: stage
					})
				});

				if (res.ok) {
					const data = await res.json();
					showStatus('matchStatus', `✓ Partita registrata! Home: ${data.home_points_awarded}pt, Away: ${data.away_points_awarded}pt`, 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('matchStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('matchStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function deleteSquadHandler(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('deleteStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = document.getElementById('deleteSquadSelect').value;
			try {
				await fetch(`${API_BASE}/participants/${squadId}`, {
					method: 'DELETE',
					headers: { 'X-Admin-Token': token }
				});
				window.location.reload();
			} catch (err) {
				showStatus('deleteStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function assignPoints(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('pointsStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = parseInt(document.getElementById('pointsSquad').value);
			const points = parseInt(document.getElementById('pointsAmount').value);

			try {
				const res = await fetch(`${API_BASE}/participants/${squadId}/points`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({ points: points })
				});

				if (res.ok) {
					showStatus('pointsStatus', '✓ Punti assegnati', 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('pointsStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('pointsStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function removePoints(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('removePointsStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = parseInt(document.getElementById('removePointsSquad').value);
			const pointsToRemove = parseInt(document.getElementById('removePointsAmount').value);
			const selectedSquad = lastSquads.find(s => Number(s.id) === squadId);

			if (!selectedSquad) {
				showStatus('removePointsStatus', '✗ Seleziona una squadra valida', 'error');
				return;
			}

			const currentScore = parseInt(selectedSquad.score || 0);
			const newScore = Math.max(0, currentScore - pointsToRemove);
			const confirmed = window.confirm(`Rimuovere ${pointsToRemove} punti da ${selectedSquad.name}? Punteggio attuale: ${currentScore}, nuovo punteggio: ${newScore}`);
			if (!confirmed) {
				showStatus('removePointsStatus', 'Operazione annullata', 'error');
				return;
			}

			try {
				const res = await fetch(`${API_BASE}/participants/${squadId}/points`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({ points: newScore })
				});

				if (res.ok) {
					showStatus('removePointsStatus', `✓ Punti rimossi. Nuovo punteggio: ${newScore}`, 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('removePointsStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('removePointsStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function loadSquads() {
			try {
				const res = await fetch(`${API_BASE}/participants`);
				const squads = await res.json();
				lastSquads = squads;

				const rows = squads.map(s => `
					<tr>
						<td>${s.id}</td>
						<td>${s.name || 'N/A'}</td>
						<td>${s.role || '-'}</td>
						<td>${s.cost || 0} DomeCoin</td>
						<td>${s.score || 0}</td>
					</tr>
				`).join('');

				document.getElementById('squadsTable').innerHTML = rows ||
					'<tr><td colspan="5" style="text-align: center; color: #9ca3af;">Nessuna squadra</td></tr>';

				const options = squads.map(s => `<option value="${s.id}">${s.name} (${s.role})</option>`).join('');
				const defaultOpt = '<option value="">Seleziona squadra</option>';
				document.getElementById('homeSquad').innerHTML = defaultOpt + options;
				document.getElementById('awaySquad').innerHTML = defaultOpt + options;
				document.getElementById('pointsSquad').innerHTML = defaultOpt + options;
				document.getElementById('removePointsSquad').innerHTML = defaultOpt + options;
				document.getElementById('deleteSquadSelect').innerHTML = defaultOpt + options;
			} catch (err) {
				console.error('Errore:', err);
			}
		}

		async function loadTeams() {
			try {
				const res = await fetch(`${API_BASE}/teams`);
				const teams = await res.json();

				const rows = teams.map(t => `
					<tr>
						<td>${t.id}</td>
						<td>${t.name || 'N/A'}</td>
						<td>${t.score || 0}</td>
						<td>${t.total_cost || 0} DomeCoin</td>
						<td>${t.balance_credits || 0}</td>
					</tr>
				`).join('');

				document.getElementById('teamsTable').innerHTML = rows ||
					'<tr><td colspan="5" style="text-align: center; color: #9ca3af;">Nessun team</td></tr>';
			} catch (err) {
				console.error('Errore:', err);
			}
		}

		document.addEventListener('DOMContentLoaded', initAdminToken);
	</script>
</body>
</html>
"""

	return HTMLResponse(content=html)
