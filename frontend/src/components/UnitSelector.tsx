type Props = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  id?: string;
};

const UNIT_GROUPS: { label: string; units: string[] }[] = [
  { label: "Poids",   units: ["g", "kg"] },
  { label: "Volume",  units: ["ml", "cl", "L"] },
  { label: "Cuisine", units: ["c. à soupe", "c. à thé", "tasse"] },
  { label: "Compte",  units: ["piece", "botte", "tranche", "boîte", "paquet", "gousse"] },
  { label: "Autre",   units: ["pincée", "au goût", "filet"] },
];

export function UnitSelector({ value, onChange, className, id }: Readonly<Props>) {
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      {UNIT_GROUPS.map((group) => (
        <optgroup key={group.label} label={group.label}>
          {group.units.map((unit) => (
            <option key={unit} value={unit}>
              {unit}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
