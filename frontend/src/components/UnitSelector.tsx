import { useTranslation } from "react-i18next";

type Props = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  id?: string;
};

const UNIT_GROUPS: { key: string; units: string[] }[] = [
  { key: "Weight",  units: ["g", "kg"] },
  { key: "Volume",  units: ["ml", "cl", "L"] },
  { key: "Cooking", units: ["c. à soupe", "c. à thé", "tasse"] },
  { key: "Count",   units: ["piece", "botte", "tranche", "boîte", "paquet", "gousse"] },
  { key: "Other",   units: ["pincée", "au goût", "filet"] },
];

export function UnitSelector({ value, onChange, className, id }: Readonly<Props>) {
  const { t } = useTranslation();
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      {UNIT_GROUPS.map((group) => (
        <optgroup key={group.key} label={t(`unit.group.${group.key}`)}>
          {group.units.map((unit) => (
            <option key={unit} value={unit}>
              {t(`unit.${unit}`)}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
