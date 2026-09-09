/* Prescribing — the medicine half of the "Docon" reference, adapted to this
   console's already-built shape: it reuses Catalogue (search, frequent
   chips, A–Z sections) exactly like AdvicePanel does, so a doctor learns one
   selection pattern for both advice and medicines.

   Templates are private per doctor (confirmed decision): applying one fills
   both the medicine list and the advice selection in one action; saving one
   captures whatever is currently selected under a name the doctor chooses.
   Starter templates exist per specialty, copied into a new doctor's own
   library at signup — from that point each doctor's copy is independently
   editable, same as anything created from scratch here. */

import { useEffect, useMemo, useState } from "react";
import { fetchMedicines, fetchTemplates, createTemplate } from "../api/client.js";
import Catalogue from "./Catalogue.jsx";

export default function MedicinePanel({ selected, onChange, advice, onApplyAdvice, adviceLibrary }) {
  const [library, setLibrary] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");

  useEffect(() => {
    let alive = true;
    fetchMedicines().then((l) => alive && setLibrary(l));
    fetchTemplates().then((t) => alive && setTemplates(t));
    return () => {
      alive = false;
    };
  }, []);

  const selectedNames = useMemo(() => new Set(selected.map((s) => s.name)), [selected]);
  const catalogueItems = useMemo(
    () => library.map((m) => ({ id: m.id, text: m.strength ? `${m.name} · ${m.strength}` : m.name, used_count: m.used_count, _medicine: m })),
    [library]
  );
  const selectedIds = useMemo(
    () => new Set(catalogueItems.filter((it) => selectedNames.has(it._medicine.name)).map((it) => it.id)),
    [catalogueItems, selectedNames]
  );

  function toggle(item) {
    const m = item._medicine;
    if (selectedNames.has(m.name)) {
      onChange(selected.filter((s) => s.name !== m.name));
    } else {
      onChange([...selected, { name: m.name, dosage: m.strength || "", frequency: "", duration: "" }]);
    }
  }

  function updateField(name, field, value) {
    onChange(selected.map((s) => (s.name === name ? { ...s, [field]: value } : s)));
  }

  function removeMedicine(name) {
    onChange(selected.filter((s) => s.name !== name));
  }

  function applyTemplate(templateId) {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    onChange(tpl.medicines.map((m) => ({ name: m.name, dosage: m.dosage || "", frequency: m.frequency || "", duration: m.duration || "" })));
    if (onApplyAdvice && adviceLibrary?.length) {
      const entries = adviceLibrary.filter((a) => tpl.advice_ids.includes(a.id));
      onApplyAdvice(entries);
    }
  }

  async function saveTemplate(e) {
    e.preventDefault();
    const name = templateName.trim();
    if (!name) return;
    const saved = await createTemplate({
      name,
      diagnosis_label: null,
      medicines: selected,
      advice_ids: advice.map((a) => a.id),
    });
    setTemplates((prev) => [...prev, saved]);
    setTemplateName("");
    setSavingTemplate(false);
  }

  return (
    <section className="band medicine" aria-labelledby="medicine-h">
      <h2 className="bandhead" id="medicine-h">
        Medicines
      </h2>

      <div className="med-toolbar">
        <label className="med-tpl-picker">
          Apply template
          <select defaultValue="" onChange={(e) => e.target.value && applyTemplate(e.target.value)}>
            <option value="" disabled>
              {templates.length ? "Choose…" : "No templates yet"}
            </option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>

        {savingTemplate ? (
          <form className="med-tpl-save" onSubmit={saveTemplate}>
            <input
              autoFocus
              placeholder="Template name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              aria-label="Template name"
            />
            <button type="submit" className="btn btn-primary" disabled={!templateName.trim() || !selected.length}>
              Save
            </button>
            <button type="button" className="btn" onClick={() => { setSavingTemplate(false); setTemplateName(""); }}>
              Cancel
            </button>
          </form>
        ) : (
          <button type="button" className="btn" disabled={!selected.length} onClick={() => setSavingTemplate(true)}>
            Save as template
          </button>
        )}
      </div>

      {selected.length ? (
        <ul className="med-chosen">
          {selected.map((s) => (
            <li key={s.name} className="med-pick">
              <span className="med-name">{s.name}</span>
              <input
                className="med-field"
                placeholder="Dose"
                value={s.dosage}
                onChange={(e) => updateField(s.name, "dosage", e.target.value)}
                aria-label={`${s.name} dosage`}
              />
              <input
                className="med-field"
                placeholder="Frequency"
                value={s.frequency}
                onChange={(e) => updateField(s.name, "frequency", e.target.value)}
                aria-label={`${s.name} frequency`}
              />
              <input
                className="med-field"
                placeholder="Duration"
                value={s.duration}
                onChange={(e) => updateField(s.name, "duration", e.target.value)}
                aria-label={`${s.name} duration`}
              />
              <button type="button" className="advice-remove" aria-label={`Remove ${s.name}`} onClick={() => removeMedicine(s.name)}>
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="advice-empty">Nothing prescribed yet. Search below or apply a template.</p>
      )}

      <Catalogue
        items={catalogueItems}
        selectedIds={selectedIds}
        onToggle={toggle}
        searchPlaceholder="Search medicines"
      />
    </section>
  );
}
