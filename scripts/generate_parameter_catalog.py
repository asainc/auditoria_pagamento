"""Gera o catálogo TypeScript a partir da política central versionada."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config/calculation_policy.json"
TARGET = ROOT / "frontend/src/app/calculation/parameter-fields.ts"


def ts(value: object) -> str:
    """Serializa JSON válido também como literal TypeScript."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    """Valida chaves básicas e grava o artefato consumido pela interface."""
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    fields = data["fields"]
    keys = [field["key"] for field in fields]
    if len(keys) != len(set(keys)):
        raise ValueError("Há parâmetros duplicados em calculation_policy.json.")
    content = f'''/** Gerado de config/calculation_policy.json. Não editar manualmente. */
import {{ CalculationParameters_Input }} from '../core/contracts';

export type ParameterKey = keyof CalculationParameters_Input;
export type DamageType = 'dano_material' | 'dano_moral' | 'honorarios' | 'custas';
export interface SelectOption {{value: string | number | boolean | null; label: string; hidden?: boolean;}}
export interface ParamField {{key: ParameterKey; label: string; type: 'text' | 'number' | 'date' | 'select' | 'checkbox'; section: string; options?: SelectOption[]; help?: string; damageTypes?: DamageType[];}}

export const PARAM_FIELDS: ParamField[] = {ts(fields)} as ParamField[];
export const REQUIRED_PARAMETER_KEYS: ParameterKey[] = {ts(data['required_parameter_keys'])} as ParameterKey[];
export const MANUAL_DEFAULT_PARAMETERS: Partial<CalculationParameters_Input> = {ts(data['origins']['manual']['defaults'])};
export const PROCESS_DEFAULT_PARAMETERS: Partial<CalculationParameters_Input> = {ts(data['origins']['processo']['defaults'])};

function optionsFor(key: ParameterKey): SelectOption[] {{
  return PARAM_FIELDS.find(field => field.key === key)?.options ?? [];
}}

export const monthOptions = optionsFor('mes_atualizacao');
export const interestTypeOptions = optionsFor('juros_moratorios_tipo');
export const periodicityOptions = optionsFor('juros_moratorios_periodicidade');
export const feeTypeOptions = optionsFor('honorarios_tipo');
export const prescricaoReferenceOptions = optionsFor('prescricao_data_referencia_tipo');
export const compensationTypeOptions = optionsFor('compensacao_tipo_calculo');
'''
    TARGET.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
