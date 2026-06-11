import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Without vitest `globals: true`, testing-library cannot register its own
// automatic cleanup — do it explicitly so renders don't leak across tests.
afterEach(cleanup);
