/**
 * Toast notification component.
 */
import { createElement } from "react";
import htm from "htm";

const html = htm.bind(createElement);

export function Toast({ message, type = "success" }) {
  return html`
    <div class="toast toast-${type}">
      <span class="toast-icon">${type === "success" ? "\u2713" : "\u2717"}</span>
      <span class="toast-message">${message}</span>
    </div>
  `;
}
