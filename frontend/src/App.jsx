import { useState, useEffect } from "react";

const API = "/api";
const STATUS_LABELS = { todo: "A faire", in_progress: "En cours", done: "Termine" };
const STATUS_NEXT = { todo: "in_progress", in_progress: "done", done: null };
const STATUS_COLORS = { todo: "#6b7280", in_progress: "#f59e0b", done: "#10b981" };
const STATUS_BG = { todo: "#f8fafc", in_progress: "#fffbeb", done: "#f0fdf4" };

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editingTask, setEditingTask] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  async function fetchTasks() {
    try {
      const res = await fetch(API + "/tasks");
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setTasks(data);
      setError(null);
    } catch (e) {
      setError("Erreur de chargement : " + e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchTasks(); }, []);

  async function createTask(e) {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      const res = await fetch(API + "/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      setTitle(""); setDescription(""); fetchTasks();
    } catch (e) { setError("Erreur creation : " + e.message); }
  }

  async function saveEdit(task) {
    try {
      const res = await fetch(API + "/tasks/" + task.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle, description: editDescription }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      setEditingTask(null);
      fetchTasks();
    } catch (e) { setError("Erreur modification : " + e.message); }
  }

  async function advanceStatus(task) {
    const next = STATUS_NEXT[task.status];
    if (!next) return;
    try {
      const res = await fetch(API + "/tasks/" + task.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      fetchTasks();
    } catch (e) { setError("Erreur avancement : " + e.message); }
  }

  async function deleteTask(id) {
    if (!window.confirm("Supprimer cette tache ?")) return;
    try {
      await fetch(API + "/tasks/" + id, { method: "DELETE" });
      fetchTasks();
    } catch (e) { setError("Erreur suppression : " + e.message); }
  }

  function startEdit(task) {
    setEditingTask(task.id);
    setEditTitle(task.title);
    setEditDescription(task.description || "");
  }

  return (
    <div style={s.page}>

      <div style={s.header}>
        <div>
          <h1 style={s.title}>OpsTasks</h1>
          <p style={s.subtitle}>Gestionnaire de taches operationnelles</p>
        </div>
        <div style={s.statsRow}>
          {["todo","in_progress","done"].map(st => (
            <div key={st} style={{...s.statBox, borderColor: STATUS_COLORS[st]}}>
              <span style={{color: STATUS_COLORS[st], fontWeight: 700, fontSize: "2rem"}}>
                {tasks.filter(t => t.status === st).length}
              </span>
              <span style={s.statLabel}>{STATUS_LABELS[st]}</span>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div style={s.errorBox}>
          <span>{error}</span>
          <button style={s.closeBtn} onClick={() => setError(null)}>Fermer</button>
        </div>
      )}

      <div style={s.card}>
        <h2 style={s.cardTitle}>Nouvelle tache</h2>
        <div style={s.form}>
          <input style={s.input} type="text" placeholder="Titre (obligatoire)"
            value={title} onChange={e => setTitle(e.target.value)} maxLength={120} />
          <input style={s.input} type="text" placeholder="Description (optionnel)"
            value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} />
          <button style={s.btnAdd} onClick={createTask}>Ajouter</button>
        </div>
      </div>

      {loading ? (
        <p style={s.muted}>Chargement...</p>
      ) : tasks.length === 0 ? (
        <div style={s.emptyState}>
          <p style={{color:"#94a3b8", fontSize:"1.1rem"}}>Aucune tache. Creez-en une !</p>
        </div>
      ) : (
        <div style={s.taskList}>
          {tasks.map(task => (
            <div key={task.id} style={{...s.taskCard, borderLeft: "6px solid " + STATUS_COLORS[task.status], background: STATUS_BG[task.status]}}>
              {editingTask === task.id ? (
                <div style={s.editForm}>
                  <input style={s.input} value={editTitle}
                    onChange={e => setEditTitle(e.target.value)} maxLength={120} placeholder="Titre" />
                  <input style={s.input} value={editDescription}
                    onChange={e => setEditDescription(e.target.value)} maxLength={1000} placeholder="Description" />
                  <div style={s.actRow}>
                    <button style={s.btnSave} onClick={() => saveEdit(task)}>Sauvegarder</button>
                    <button style={s.btnCancel} onClick={() => setEditingTask(null)}>Annuler</button>
                  </div>
                </div>
              ) : (
                <div style={s.taskInner}>
                  <div style={s.taskLeft}>
                    <div style={s.taskTopRow}>
                      <span style={{...s.badge, background: STATUS_COLORS[task.status]}}>
                        {STATUS_LABELS[task.status]}
                      </span>
                      <span style={s.taskDate}>
                        {new Date(task.created_at).toLocaleDateString("fr-FR")}
                      </span>
                    </div>
                    <p style={s.taskTitle}>{task.title}</p>
                    {task.description && <p style={s.taskDesc}>{task.description}</p>}
                  </div>
                  <div style={s.taskActions}>
                    {STATUS_NEXT[task.status] && (
                      <button style={s.btnAdvance} onClick={() => advanceStatus(task)}>
                        Avancer
                      </button>
                    )}
                    <button style={s.btnEdit} onClick={() => startEdit(task)}>Modifier</button>
                    <button style={s.btnDelete} onClick={() => deleteTask(task.id)}>Supprimer</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const s = {
  page: { maxWidth: "100%", margin: 0, padding: "2.5rem 4rem", fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#f1f5f9" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem", flexWrap: "wrap", gap: "1rem" },
  title: { fontSize: "2.2rem", fontWeight: 700, color: "#1e293b", margin: 0 },
  subtitle: { color: "#64748b", margin: "0.4rem 0 0 0", fontSize: "1rem" },
  statsRow: { display: "flex", gap: "1rem" },
  statBox: { background: "#fff", border: "2px solid", borderRadius: 12, padding: "1rem 1.75rem", textAlign: "center", minWidth: 110, display: "flex", flexDirection: "column", gap: "0.2rem", boxShadow: "0 1px 4px rgba(0,0,0,0.07)" },
  statLabel: { fontSize: "0.85rem", color: "#64748b", fontWeight: 500 },
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1.75rem", marginBottom: "2rem", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" },
  cardTitle: { fontSize: "1.1rem", fontWeight: 600, color: "#334155", marginTop: 0, marginBottom: "1.25rem" },
  form: { display: "flex", gap: "0.75rem", flexWrap: "wrap" },
  input: { flex: 1, minWidth: 200, padding: "0.75rem 1rem", border: "1px solid #cbd5e1", borderRadius: 8, fontSize: "1rem", outline: "none", background: "#fff" },
  btnAdd: { padding: "0.75rem 2rem", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: "0.95rem", whiteSpace: "nowrap", letterSpacing: "0.02em" },
  taskList: { display: "flex", flexDirection: "column", gap: "0.75rem" },
  taskCard: { background: "#fff", borderRadius: 10, padding: "1.25rem 1.75rem", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  taskInner: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" },
  taskLeft: { flex: 1 },
  taskTopRow: { display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" },
  badge: { color: "#fff", fontSize: "0.78rem", padding: "0.25rem 0.85rem", borderRadius: 999, fontWeight: 600, letterSpacing: "0.03em" },
  taskDate: { fontSize: "0.82rem", color: "#94a3b8" },
  taskTitle: { fontWeight: 600, color: "#1e293b", margin: "0 0 0.25rem 0", fontSize: "1.05rem" },
  taskDesc: { color: "#64748b", fontSize: "0.9rem", margin: 0 },
  taskActions: { display: "flex", gap: "0.5rem", flexShrink: 0 },
  btnAdvance: { padding: "0.45rem 1rem", background: "#dbeafe", color: "#1d4ed8", border: "1px solid #bfdbfe", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem", fontWeight: 500, letterSpacing: "0.02em" },
  btnEdit: { padding: "0.45rem 1rem", background: "#fef9c3", color: "#92400e", border: "1px solid #fde68a", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem", fontWeight: 500 },
  btnDelete: { padding: "0.45rem 1rem", background: "#fee2e2", color: "#dc2626", border: "1px solid #fca5a5", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem", fontWeight: 500 },
  btnSave: { padding: "0.5rem 1.25rem", background: "#10b981", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.95rem", fontWeight: 600 },
  btnCancel: { padding: "0.5rem 1.25rem", background: "#f1f5f9", color: "#475569", border: "1px solid #cbd5e1", borderRadius: 6, cursor: "pointer", fontSize: "0.95rem" },
  editForm: { display: "flex", flexDirection: "column", gap: "0.75rem" },
  actRow: { display: "flex", gap: "0.75rem" },
  errorBox: { background: "#fee2e2", color: "#dc2626", border: "1px solid #fca5a5", borderRadius: 8, padding: "1rem 1.5rem", marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" },
  closeBtn: { background: "none", border: "none", cursor: "pointer", color: "#dc2626", fontWeight: 600, fontSize: "0.9rem" },
  muted: { textAlign: "center", color: "#94a3b8", padding: "3rem", fontSize: "1.1rem" },
  emptyState: { textAlign: "center", padding: "4rem", background: "#fff", borderRadius: 12, border: "1px dashed #cbd5e1" },
};
