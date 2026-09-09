"use client";

import { FormEvent, useState } from "react";
import { Button } from "./ui/Button";

const AUDIT_EMAIL = "veriiaudit@gmail.com";

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);

    const name = String(data.get("name") ?? "");
    const email = String(data.get("email") ?? "");
    const organization = String(data.get("organization") ?? "");
    const system = String(data.get("system") ?? "");
    const languages = String(data.get("languages") ?? "");
    const goal = String(data.get("goal") ?? "");
    const message = String(data.get("message") ?? "");

    const subject = `VERIAUDIT audit request — ${organization || name}`;
    const body = [
      `Name: ${name}`,
      `Email: ${email}`,
      `Organization: ${organization}`,
      `Model / System: ${system}`,
      `Languages: ${languages}`,
      `Evaluation goal: ${goal}`,
      "",
      "Message:",
      message,
    ].join("\n");

    window.location.href = `mailto:${AUDIT_EMAIL}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(body)}`;
    setSubmitted(true);
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 max-w-xl">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name" name="name" required />
        <Field label="Email" name="email" type="email" required />
      </div>
      <Field label="Organization" name="organization" />
      <Field label="Model / System" name="system" placeholder="e.g. a fine-tuned open-weight model" />
      <Field label="Languages" name="languages" placeholder="e.g. Urdu, Roman Urdu" />
      <Field label="Evaluation goal" name="goal" placeholder="e.g. pre-launch safety audit" />
      <div>
        <label className="block text-xs font-medium text-ink-muted mb-1.5" htmlFor="message">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={5}
          className="w-full resize-none rounded-lg border border-border bg-bg-raised px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" variant="primary">
          Request an Audit
        </Button>
        {submitted && (
          <span className="text-xs text-ink-muted">
            Opening your email client to {AUDIT_EMAIL}…
          </span>
        )}
      </div>
      <p className="text-xs text-ink-faint">
        Submitting opens a pre-filled email to {AUDIT_EMAIL} via your default mail client — this
        form does not transmit data to a server.
      </p>
    </form>
  );
}

function Field({
  label,
  name,
  type = "text",
  required,
  placeholder,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-ink-muted mb-1.5" htmlFor={name}>
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        required={required}
        placeholder={placeholder}
        className="w-full rounded-lg border border-border bg-bg-raised px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
      />
    </div>
  );
}
