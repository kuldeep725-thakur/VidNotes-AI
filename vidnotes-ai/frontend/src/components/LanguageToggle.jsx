const OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'hinglish', label: 'Hinglish' },
];

export default function LanguageToggle({ value, onChange }) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Notes language">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={value === option.value ? 'active' : ''}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
