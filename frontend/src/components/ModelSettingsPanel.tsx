import { useEffect, useState } from "react";
import { api, type ModelSettings, type ModelSettingsResponse, type ModelTestResponse } from "../api/client";

type Props = {
  onStatus: (message: string) => void;
};

const DEFAULT_SETTINGS: ModelSettings = {
  base_url: "https://ai.dianhuomao.shop/v1",
  api_key: "",
  model: "【J-C思考】gemini-2.5-pro（3）",
  temperature: 0.2,
  max_tokens: 1024,
  timeout: 120,
  vision_enabled: true,
};

export function ModelSettingsPanel({ onStatus }: Props) {
  const [settings, setSettings] = useState<ModelSettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState<ModelSettingsResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [testResult, setTestResult] = useState<ModelTestResponse | null>(null);

  useEffect(() => {
    void loadSettings();
  }, []);

  async function loadSettings() {
    const response = await api.getModelSettings();
    setSaved(response);
    setSettings((current) => ({
      ...current,
      base_url: response.base_url,
      model: response.model,
      temperature: response.temperature,
      max_tokens: response.max_tokens,
      timeout: response.timeout,
      vision_enabled: response.vision_enabled,
      api_key: "",
    }));
  }

  async function handleSave() {
    try {
      setSaving(true);
      const response = await api.saveModelSettings(settings);
      setSaved(response);
      setSettings((current) => ({ ...current, api_key: "" }));
      setTestResult(null);
      onStatus("模型设置已保存。");
    } catch (error) {
      onStatus(String(error));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    try {
      setTesting(true);
      const response = await api.testModelSettings(settings);
      setTestResult(response);
      onStatus(response.message);
    } catch (error) {
      onStatus(String(error));
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="panel side-panel collapsible-panel">
      <div className="panel-title-row panel-toggle-row">
        <div>
          <h2>模型后端</h2>
          <p className="mini-muted">{saved?.model || settings.model}</p>
        </div>
        <button className="ghost-button" type="button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "收起" : "展开"}
        </button>
      </div>
      <div className="settings-summary">
        <span>总站：{saved?.base_url || settings.base_url}</span>
        <span>Timeout：{saved?.timeout ?? settings.timeout}</span>
        <span>{saved?.api_key_set ? `已配置 ${saved.api_key_masked}` : "未配置 API key"}</span>
      </div>
      {expanded ? (
        <div className="settings-form-body">
          <label>
            Base URL
            <input value={settings.base_url} onChange={(event) => setSettings({ ...settings, base_url: event.target.value })} />
          </label>
          <label>
            API Key
            <input type="password" value={settings.api_key ?? ""} onChange={(event) => setSettings({ ...settings, api_key: event.target.value })} placeholder={saved?.api_key_masked || "sk-..."} />
          </label>
          <label>
            Model Name
            <input value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })} />
          </label>
          <label>
            Temperature
            <input type="number" step="0.1" value={settings.temperature} onChange={(event) => setSettings({ ...settings, temperature: Number(event.target.value) })} />
          </label>
          <label>
            Max Tokens
            <input type="number" value={settings.max_tokens} onChange={(event) => setSettings({ ...settings, max_tokens: Number(event.target.value) })} />
          </label>
          <label>
            Timeout
            <input type="number" value={settings.timeout} onChange={(event) => setSettings({ ...settings, timeout: Number(event.target.value) })} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={settings.vision_enabled} onChange={(event) => setSettings({ ...settings, vision_enabled: event.target.checked })} />
            <span>Vision Enabled</span>
          </label>
          <div className="button-row">
            <button disabled={saving} onClick={handleSave}>保存</button>
            <button disabled={testing} onClick={handleTest}>测试连接</button>
          </div>
          {testResult ? <div className="thought-box compact-thought-box">{testResult.message}{testResult.raw_response ? `\n${testResult.raw_response}` : ""}</div> : null}
        </div>
      ) : null}
    </section>
  );
}

