import axios from "axios";
import {tr} from "./i18n/core";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 20000,
});
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
export function errorText(error) {
  const d = error.response?.data?.detail;
  return tr(typeof d === "string"
    ? d
    : Array.isArray(d)
      ? d.map((x) => x.msg).join(", ")
      : "Unable to connect. Please try again.");
}
export async function download(path, name) {
  const r = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
