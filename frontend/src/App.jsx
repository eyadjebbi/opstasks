import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API = "/api";
const STATUSES = ["todo", "in_progress", "done"];
const STATUS_LABELS = {
  todo: "A faire",
  in_progress: "En cours",
  done: "Termine",
};

function validationMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((entry) => entry.message || entry.msg).filter(Boolean).join("; ");
  }
  return null;
}

async function apiRequest(path, options) {
  const response = await fetch(path, options);
  if (response.ok) {
    return response.status === 204 ? null : response.json();
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // A proxy or network component may return an empty, non-JSON error body.
  }
  throw new Error(validationMessage(payload?.detail) || `Requete refusee (${response.status})`);
}

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiHealthy, setApiHealthy] = useState(null);
  const [editingTask, setEditingTask] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const fetchTasks = useCallback(async () => {
    try {
      const data = await apiRequest(`${API}/tasks`);
      setTasks(data);
      setError(null);
    } catch (requestError) {
      setError(`Erreur de chargement : ${requestError.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch("/health/ready");
      setApiHealthy(response.ok);
    } catch {
      setApiHealthy(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    checkHealth();
    const healthTimer = window.setInterval(checkHealth, 10_000);
    return () => window.clearInterval(healthTimer);
  }, [checkHealth, fetchTasks]);

  async function createTask(event) {
    event.preventDefault();
    if (!title.trim()) {
      setError("Le titre est obligatoire.");
      return;
    }
    try {
      await apiRequest(`${API}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });
      setTitle("");
      setDescription("");
      await fetchTasks();
    } catch (requestError) {
      setError(`Erreur creation : ${requestError.message}`);
    }
  }

  async function saveEdit(task) {
    try {
      await apiRequest(`${API}/tasks/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle, description: editDescription }),
      });
      setEditingTask(null);
      await fetchTasks();
    } catch (requestError) {
      setError(`Erreur modification : ${requestError.message}`);
    }
  }

  async function changeStatus(task, status) {
    if (status === task.status) return;
    try {
      await apiRequest(`${API}/tasks/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await fetchTasks();
    } catch (requestError) {
      setError(`Erreur de statut : ${requestError.message}`);
    }
  }

  async function deleteTask(id) {
    if (!window.confirm("Supprimer cette tache ?")) return;
    try {
      await apiRequest(`${API}/tasks/${id}`, { method: "DELETE" });
      await fetchTasks();
    } catch (requestError) {
      setError(`Erreur suppression : ${requestError.message}`);
    }
  }

  function startEdit(task) {
    setEditingTask(task.id);
    setEditTitle(task.title);
    setEditDescription(task.description || "");
  }

  const healthLabel = apiHealthy === null
    ? "API en verification"
    : apiHealthy ? "API disponible" : "API indisponible";

  return (
    <main className="page">
      <header className="header">
        <div>
          <div className="title-row">
            <h1>OpsTasks</h1>
            <span
              className={`health health-${apiHealthy === null ? "checking" : apiHealthy ? "up" : "down"}`}
              data-testid="api-health"
              role="status"
            >
              {healthLabel}
            </span>
          </div>
          <p className="subtitle">Gestionnaire de taches operationnelles</p>
        </div>
        <div className="stats-row">
          {STATUSES.map((status) => (
            <div className={`stat-box status-${status}`} key={status}>
              <strong>{tasks.filter((task) => task.status === status).length}</strong>
              <span>{STATUS_LABELS[status]}</span>
            </div>
          ))}
        </div>
      </header>

      {error && (
        <div className="error-box" role="alert">
          <span>{error}</span>
          <button className="close-button" onClick={() => setError(null)}>Fermer</button>
        </div>
      )}

      <section className="card">
        <h2>Nouvelle tache</h2>
        <form className="form" onSubmit={createTask}>
          <input
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Titre (obligatoire)"
            value={title}
          />
          <input
            maxLength={1000}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description (optionnel)"
            value={description}
          />
          <button className="button-add" type="submit">Ajouter</button>
        </form>
      </section>

      {loading ? (
        <p className="message">Chargement...</p>
      ) : tasks.length === 0 ? (
        <div className="empty-state">Aucune tache. Creez-en une !</div>
      ) : (
        <section className="task-list" aria-label="Taches">
          {tasks.map((task) => (
            <article className={`task-card status-${task.status}`} key={task.id}>
              {editingTask === task.id ? (
                <div className="edit-form">
                  <input maxLength={120} onChange={(event) => setEditTitle(event.target.value)} value={editTitle} />
                  <input maxLength={1000} onChange={(event) => setEditDescription(event.target.value)} value={editDescription} />
                  <div className="actions">
                    <button className="button-save" onClick={() => saveEdit(task)}>Sauvegarder</button>
                    <button className="button-cancel" onClick={() => setEditingTask(null)}>Annuler</button>
                  </div>
                </div>
              ) : (
                <div className="task-inner">
                  <div className="task-content">
                    <div className="task-meta">
                      <span className="badge">{STATUS_LABELS[task.status]}</span>
                      <span>{new Date(task.created_at).toLocaleDateString("fr-FR")}</span>
                    </div>
                    <h3>{task.title}</h3>
                    {task.description && <p>{task.description}</p>}
                  </div>
                  <div className="actions">
                    <label className="visually-hidden" htmlFor={`status-${task.id}`}>Statut de {task.title}</label>
                    <select
                      aria-label={`Statut de ${task.title}`}
                      id={`status-${task.id}`}
                      onChange={(event) => changeStatus(task, event.target.value)}
                      value={task.status}
                    >
                      {STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
                    </select>
                    <button className="button-edit" onClick={() => startEdit(task)}>Modifier</button>
                    <button className="button-delete" onClick={() => deleteTask(task.id)}>Supprimer</button>
                  </div>
                </div>
              )}
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
