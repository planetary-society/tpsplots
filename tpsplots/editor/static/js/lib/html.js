/**
 * Shared htm + React binding. Import { html } from here instead of
 * repeating the three-line htm.bind(createElement) boilerplate.
 */
import { createElement } from "react";
import htm from "htm";

export const html = htm.bind(createElement);
