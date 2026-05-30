/**
 * stream.test.ts
 * Tests for the streamIncident() SSE helper.
 * We mock EventSource since jsdom doesn't implement it.
 */
import { streamIncident, ApiException } from "../lib/apis";
import Cookies from "js-cookie";

jest.mock("js-cookie", () => ({ get: jest.fn() }));
const mockCookies = Cookies as jest.Mocked<typeof Cookies>;

// ---------------------------------------------------------------------------
// Minimal EventSource mock
// ---------------------------------------------------------------------------
type Listener = (e: MessageEvent) => void;

class MockEventSource {
  url: string;
  listeners: Record<string, Listener[]> = {};
  onerror: (() => void) | null = null;
  static instance: MockEventSource;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instance = this;
  }

  addEventListener(type: string, fn: Listener) {
    this.listeners[type] = this.listeners[type] ?? [];
    this.listeners[type].push(fn);
  }

  emit(type: string, data: unknown) {
    (this.listeners[type] ?? []).forEach((fn) =>
      fn({ data: JSON.stringify(data) } as MessageEvent),
    );
  }

  close = jest.fn();
}

beforeEach(() => {
  jest.clearAllMocks();
  (mockCookies.get as jest.Mock).mockReturnValue(undefined);
  (global as unknown as { EventSource: typeof MockEventSource }).EventSource =
    MockEventSource;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("streamIncident()", () => {
  it("calls onEvent for each SSE event type", () => {
    const onEvent = jest.fn();
    const onDone = jest.fn();
    const onError = jest.fn();

    streamIncident("checkout down", null, "", [], onEvent, onDone, onError);

    const es = MockEventSource.instance;
    es.emit("step", { agent: "classifier", step: "classify", status: "ok" });
    es.emit("result", { agent: "remediator", step: "fix", status: "done" });

    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onEvent.mock.calls[0][0]).toMatchObject({
      event: "step",
      agent: "classifier",
    });
    expect(onEvent.mock.calls[1][0]).toMatchObject({
      event: "result",
      agent: "remediator",
    });
  });

  it("calls onDone with session_id on done event", () => {
    const onDone = jest.fn();
    streamIncident("q", null, "", [], jest.fn(), onDone, jest.fn());

    MockEventSource.instance.emit("done", { session_id: "sess-xyz" });
    expect(onDone).toHaveBeenCalledWith("sess-xyz");
    expect(MockEventSource.instance.close).toHaveBeenCalled();
  });

  it("calls onError with ApiException on error_event", () => {
    const onError = jest.fn();
    streamIncident("q", null, "", [], jest.fn(), jest.fn(), onError);

    MockEventSource.instance.emit("error_event", {
      detail: "Agent failed",
      code: "E_AGENT",
    });
    expect(onError).toHaveBeenCalledWith(expect.any(ApiException));
    expect(MockEventSource.instance.close).toHaveBeenCalled();
  });

  it("calls onError with generic Error on onerror", () => {
    const onError = jest.fn();
    streamIncident("q", null, "", [], jest.fn(), jest.fn(), onError);

    MockEventSource.instance.onerror?.();
    expect(onError).toHaveBeenCalledWith(expect.any(ApiException));
    expect(MockEventSource.instance.close).toHaveBeenCalled();
  });

  it("appends token to URL when access token is present", () => {
    (mockCookies.get as jest.Mock).mockReturnValue("tok-abc");
    streamIncident("q", null, "", [], jest.fn(), jest.fn(), jest.fn());
    expect(MockEventSource.instance.url).toContain("token=tok-abc");
  });

  it("appends session_id to URL when provided", () => {
    streamIncident("q", "sess-1", "", [], jest.fn(), jest.fn(), jest.fn());
    expect(MockEventSource.instance.url).toContain("session_id=sess-1");
  });

  it("returns a cleanup function that closes the EventSource", () => {
    const cleanup = streamIncident(
      "q",
      null,
      "",
      [],
      jest.fn(),
      jest.fn(),
      jest.fn(),
    );
    cleanup();
    expect(MockEventSource.instance.close).toHaveBeenCalled();
  });

  it("includes document_context when non-empty", () => {
    streamIncident(
      "q",
      null,
      "some context",
      [],
      jest.fn(),
      jest.fn(),
      jest.fn(),
    );
    expect(MockEventSource.instance.url).toContain(
      "document_context=some+context",
    );
  });

  it("omits document_context when whitespace only", () => {
    streamIncident("q", null, "   ", [], jest.fn(), jest.fn(), jest.fn());
    expect(MockEventSource.instance.url).not.toContain("document_context");
  });
});
