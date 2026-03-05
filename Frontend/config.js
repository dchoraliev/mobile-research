const LOCAL_IP = "137.104.182.111";
const PORT = 8089;

const USE_LOCAL = true;

const NGROK = "subimbricately-fixable-jacquelyne.ngrok-free.dev";
const LOCAL_HTTP = `https://${NGROK}`;
const LOCAL_WS   = `wss://${NGROK}/ws`;
const PROD_HTTP  = "https://chatbackend-lf7a.onrender.com";
const PROD_WS    = "wss://chatbackend-lf7a.onrender.com/ws";

export const BACKEND_HTTP = USE_LOCAL ? LOCAL_HTTP : PROD_HTTP;
export const BACKEND_WS   = USE_LOCAL ? LOCAL_WS   : PROD_WS;