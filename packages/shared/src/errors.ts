export class ValidationError extends Error {
  path: Array<string | number>;

  constructor(message: string, path: Array<string | number> = []) {
    const normalizedPath = Array.isArray(path) ? path : [path];
    const suffix = normalizedPath.length > 0 ? ` at ${normalizedPath.join(".")}` : "";
    super(`${message}${suffix}`);
    this.name = "ValidationError";
    this.path = normalizedPath;
  }
}
