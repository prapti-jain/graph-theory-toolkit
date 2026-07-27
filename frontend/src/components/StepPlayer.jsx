import './StepPlayer.css'

/**
 * Playback controls for algorithm step animation.
 */
export default function StepPlayer({
  index,
  total,
  playing,
  speed,
  disabled = false,
  currentStep,
  onPlay,
  onPause,
  onToggle,
  onStepForward,
  onStepBack,
  onReset,
  onGoToEnd,
  onSpeedChange,
}) {
  const label =
    total === 0
      ? 'No steps'
      : `Step ${Math.max(index, 0) + (total ? 1 : 0)} / ${total}`

  return (
    <section className={`step-player ${disabled ? 'step-player--disabled' : ''}`}>
      <header className="step-player__header">
        <p className="eyebrow">Animation</p>
        <p className="step-player__count">{label}</p>
      </header>

      <div className="step-player__controls">
        <button type="button" className="btn" disabled={disabled} onClick={onReset} title="Reset">
          ⟲
        </button>
        <button
          type="button"
          className="btn"
          disabled={disabled || index <= 0}
          onClick={onStepBack}
          title="Step back"
        >
          ‹
        </button>
        <button
          type="button"
          className="btn btn--primary"
          disabled={disabled || total === 0}
          onClick={onToggle || (playing ? onPause : onPlay)}
          title={playing ? 'Pause' : 'Play'}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
        <button
          type="button"
          className="btn"
          disabled={disabled || index >= total - 1}
          onClick={onStepForward}
          title="Step forward"
        >
          ›
        </button>
        <button
          type="button"
          className="btn"
          disabled={disabled || total === 0}
          onClick={onGoToEnd}
          title="Skip to end"
        >
          »|
        </button>
      </div>

      <label className="step-player__speed field">
        <span>Speed {speed.toFixed(2)}×</span>
        <input
          type="range"
          min={0.25}
          max={3}
          step={0.25}
          value={speed}
          disabled={disabled}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
        />
      </label>

      {currentStep && (
        <p className="step-player__step mono">
          {summarizeStep(currentStep)}
        </p>
      )}
    </section>
  )
}

function summarizeStep(step) {
  const action = step.action || 'step'
  if (step.node != null && step.from == null) {
    return `${action}: node ${step.node}`
  }
  if (step.from != null && step.to != null) {
    return `${action}: ${step.from} → ${step.to}`
  }
  if (step.edge) {
    return `${action}: edge ${step.edge[0]}–${step.edge[1]}`
  }
  if (step.path) {
    return `${action}: path len ${step.path.length}, bottleneck ${step.bottleneck ?? '—'}`
  }
  if (step.l1_delta != null) {
    return `${action}: L1 Δ=${Number(step.l1_delta).toExponential(2)}`
  }
  return action
}
