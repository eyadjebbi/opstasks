import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

const INITIAL_TASK = {
  id: 7,
  title: "Inspect logs",
  description: "Review recent errors",
  status: "todo",
  created_at: "2026-07-01T08:00:00Z",
};

function jsonResponse(body, status = 200) {
  return {
    json: vi.fn().mockResolvedValue(body),
    ok: status >= 200 && status < 300,
    status,
  };
}

function installApi(options = {}) {
  let tasks = options.tasks ? structuredClone(options.tasks) : [structuredClone(INITIAL_TASK)];
  let nextId = 20;
  const fetchMock = vi.fn(async (url, request = {}) => {
    const method = request.method || "GET";
    if (url === "/health/ready") {
      return jsonResponse({}, options.healthStatus || 200);
    }
    if (url === "/api/tasks" && method === "GET") return jsonResponse(tasks);
    if (url === "/api/tasks" && method === "POST") {
      const payload = JSON.parse(request.body);
      const created = {
        ...payload,
        id: nextId++,
        status: "todo",
        created_at: "2026-07-01T09:00:00Z",
      };
      tasks = [created, ...tasks];
      return jsonResponse(created, 201);
    }
    const match = url.match(/^\/api\/tasks\/(\d+)$/);
    if (match && method === "PATCH") {
      const id = Number(match[1]);
      const payload = JSON.parse(request.body);
      tasks = tasks.map((task) => task.id === id ? { ...task, ...payload } : task);
      return jsonResponse(tasks.find((task) => task.id === id));
    }
    if (match && method === "DELETE") {
      if (options.deleteStatus) {
        return jsonResponse({ detail: options.deleteDetail }, options.deleteStatus);
      }
      tasks = tasks.filter((task) => task.id !== Number(match[1]));
      return jsonResponse(null, 204);
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("OpsTasks interface", () => {
  it("shows loading and then the task list", async () => {
    let releaseTasks;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url === "/health/ready") return Promise.resolve(jsonResponse({}));
      return new Promise((resolve) => { releaseTasks = () => resolve(jsonResponse([INITIAL_TASK])); });
    }));
    render(<App />);

    expect(screen.getByText("Chargement...")).toBeInTheDocument();
    releaseTasks();
    expect(await screen.findByText("Inspect logs")).toBeInTheDocument();
  });

  it("creates and edits a task", async () => {
    const fetchMock = installApi({ tasks: [] });
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Aucune tache. Creez-en une !");
    await user.type(screen.getByPlaceholderText("Titre (obligatoire)"), "Check backups");
    await user.type(screen.getByPlaceholderText("Description (optionnel)"), "Before deploy");
    await user.click(screen.getByRole("button", { name: "Ajouter" }));
    expect(await screen.findByText("Check backups")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Modifier" }));
    const titleInput = screen.getByDisplayValue("Check backups");
    await user.clear(titleInput);
    await user.type(titleInput, "Check database backups");
    await user.click(screen.getByRole("button", { name: "Sauvegarder" }));
    expect(await screen.findByText("Check database backups")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/tasks", expect.objectContaining({ method: "POST" }));
  });

  it("allows every documented status transition", async () => {
    const fetchMock = installApi();
    const user = userEvent.setup();
    render(<App />);

    const status = await screen.findByRole("combobox", { name: "Statut de Inspect logs" });
    for (const value of ["in_progress", "done", "todo"]) {
      await user.selectOptions(status, value);
      await waitFor(() => expect(status).toHaveValue(value));
    }
    const updates = fetchMock.mock.calls.filter(([, request]) => request?.method === "PATCH");
    expect(updates.map(([, request]) => JSON.parse(request.body).status)).toEqual([
      "in_progress",
      "done",
      "todo",
    ]);
  });

  it("deletes a confirmed task", async () => {
    installApi();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Supprimer" }));
    expect(await screen.findByText("Aucune tache. Creez-en une !")).toBeInTheDocument();
  });

  it("shows client and API validation feedback", async () => {
    installApi({ deleteStatus: 500, deleteDetail: "Deletion unavailable" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Ajouter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le titre est obligatoire");
    await user.click(await screen.findByRole("button", { name: "Supprimer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Deletion unavailable");
  });

  it("reports available and unavailable API health", async () => {
    installApi({ healthStatus: 503 });
    render(<App />);
    expect(await screen.findByText("API indisponible")).toBeInTheDocument();
  });
});
