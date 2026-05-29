import { useCallback, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Upload, X, FileText, CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { listUploadsApi, uploadFileApi } from "@/features/uploads/api";
import type { Department, Upload as UploadType, UploadStatus } from "@/types";

const DEPTS: { value: Department; label: string }[] = [
  { value: "sales", label: "Sales" },
  { value: "marketing", label: "Marketing" },
  { value: "operations", label: "Operations" },
  { value: "finance", label: "Finance" },
  { value: "procurement", label: "Procurement" },
];

const ACCEPTED = ".csv,.xlsx,.xls";

function StatusBadge({ status }: { status: UploadStatus }) {
  const map: Record<UploadStatus, { label: string; cls: string; icon: React.ReactNode }> = {
    queued: {
      label: "Queued",
      cls: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      icon: <Clock className="w-3 h-3" />,
    },
    processing: {
      label: "Processing",
      cls: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    complete: {
      label: "Complete",
      cls: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300",
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    rejected: {
      label: "Rejected",
      cls: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
      icon: <XCircle className="w-3 h-3" />,
    },
    error: {
      label: "Error",
      cls: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
      icon: <XCircle className="w-3 h-3" />,
    },
  };

  const { label, cls, icon } = map[status] ?? map.error;

  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium", cls)}>
      {icon}
      {label}
    </span>
  );
}

function DeptBadge({ dept }: { dept: string }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded bg-muted text-xs font-medium text-muted-foreground capitalize">
      {dept}
    </span>
  );
}

function formatRows(n: number | null) {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

const PENDING_STATUSES: UploadStatus[] = ["queued", "processing"];

export function UploadsPage() {
  const [dept, setDept] = useState<Department>("sales");
  const [filterDept, setFilterDept] = useState<Department | "">("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["uploads", filterDept],
    queryFn: () => listUploadsApi(filterDept || undefined),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasPending = items.some((u: UploadType) => PENDING_STATUSES.includes(u.status));
      return hasPending ? 3000 : false;
    },
  });

  const mutation = useMutation({
    mutationFn: ({ f, d }: { f: File; d: Department }) => uploadFileApi(f, d),
    onSuccess: (upload) => {
      toast.success(`"${upload.original_name}" queued for processing.`);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["uploads"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Upload failed.";
      toast.error(msg);
    },
  });

  const pickFile = useCallback((f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["csv", "xlsx", "xls"].includes(ext)) {
      toast.error("Only CSV or Excel files are supported.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      toast.error("File exceeds the 50 MB limit.");
      return;
    }
    setFile(f);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) pickFile(f);
    },
    [pickFile],
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) pickFile(f);
    e.target.value = "";
  };

  const handleSubmit = () => {
    if (!file) return;
    mutation.mutate({ f: file, d: dept });
  };

  const uploads = data?.items ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Data Uploads</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Upload CSV or Excel files per department. Files are validated and loaded automatically.
        </p>
      </div>

      {/* Upload card */}
      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground">New Upload</h2>

        {/* Dept selector */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-foreground w-24 shrink-0">Department</label>
          <select
            value={dept}
            onChange={(e) => setDept(e.target.value as Department)}
            className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-brand-600/40"
          >
            {DEPTS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer select-none",
            dragging
              ? "border-brand-500 bg-brand-50 dark:bg-brand-900/20"
              : file
              ? "border-green-400 bg-green-50 dark:bg-green-900/20"
              : "border-border hover:border-brand-400 hover:bg-muted/40",
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={onInputChange}
          />

          {file ? (
            <div className="flex flex-col items-center gap-2">
              <FileText className="w-8 h-8 text-green-600" />
              <p className="text-sm font-medium text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB
              </p>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="mt-1 flex items-center gap-1 text-xs text-danger hover:underline"
              >
                <X className="w-3 h-3" /> Remove
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">
                Drag & drop or <span className="text-brand-600">browse</span>
              </p>
              <p className="text-xs text-muted-foreground">CSV, XLSX, XLS · max 50 MB</p>
            </div>
          )}
        </div>

        <button
          onClick={handleSubmit}
          disabled={!file || mutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {mutation.isPending ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
          ) : (
            <><Upload className="w-4 h-4" /> Upload file</>
          )}
        </button>
      </div>

      {/* History table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Upload History</h2>
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value as Department | "")}
            className="text-xs px-2 py-1 border border-border rounded-md bg-background text-foreground focus:outline-none"
          >
            <option value="">All departments</option>
            {DEPTS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : uploads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <FileText className="w-8 h-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No uploads yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">File</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Dept</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Status</th>
                  <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground">Total</th>
                  <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground">Clean</th>
                  <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground">Rejected</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {uploads.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3 font-medium text-foreground max-w-[200px] truncate">
                      {u.original_name}
                    </td>
                    <td className="px-4 py-3"><DeptBadge dept={u.dept} /></td>
                    <td className="px-4 py-3"><StatusBadge status={u.status} /></td>
                    <td className="px-4 py-3 text-right text-muted-foreground">{formatRows(u.rows_total)}</td>
                    <td className="px-4 py-3 text-right text-green-600 dark:text-green-400">{formatRows(u.rows_clean)}</td>
                    <td className="px-4 py-3 text-right text-red-500">{formatRows(u.rows_rejected)}</td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{formatDate(u.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
