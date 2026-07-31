// ── Active scenario — change this one line when switching scenarios ────────────
// S1 | S2 | S3a | S3b | S4 | S5 | S6 | S7 | S10 | S11
export const SCENARIO = "S5";

// Set to true during scenario testing to show retrieved chunks in chat
export const SHOW_DEBUG_CHUNKS = false;

// Scenarios where the raw image is sent to the LLM for native visual reasoning
export const SCENARIOS_WITH_IMAGE = [];

// Scenarios where a BLIP-generated caption is used instead of OCR as the photo's text context
export const SCENARIOS_WITH_CAPTION = ["S4"];

// Scenarios where both OCR text and a BLIP caption are generated and sent together as context
export const SCENARIOS_WITH_OCR_AND_CAPTION = ["S5"];
