"""The sidebar: API keys (a dropdown at the top) and settings. Everything stays in the session."""
import copy

import streamlit as st

from triage import config
from triage.config import MODELS, jev_is_mock, llm_is_mock


def llm_spec(provider: str, model: str, price_in: float, price_out: float) -> dict:
    """A keys-style dict for one LLM (what llm_baseline and reply expect)."""
    return {"provider": provider, "model": model, "price_in": price_in, "price_out": price_out,
            "llm_key": st.session_state.get(f"key_{provider}", "").strip(), "name": f"{provider} · {model}"}


def llm_specs() -> list[dict]:
    """Every LLM that can be compared: the built-in list plus a custom one, if set."""
    specs = [llm_spec(p, m, *prices) for p, models in MODELS.items() for m, prices in models.items()]
    custom = st.session_state.get("custom_model")
    if custom:
        specs.append(llm_spec(*custom))
    return specs


def sidebar() -> None:
    """API keys at the top (a dropdown that closes once Jev's key is set), then settings. Session only."""
    ss = st.session_state
    with st.sidebar:
        # Closed once the Jev key is set
        with st.expander("API keys", expanded=not ss.get("jev_key"), icon=":material/key:"):
            st.text_input("Jev", type="password", key="jev_key", help="From typesafe.ai")
            for provider in MODELS:
                st.text_input(provider, type="password", key=f"key_{provider}", help="Optional")
            st.caption("Kept in this session only, never saved. An empty key runs that model in demo mode.")

            names = [f"{p} · {m}" for p, models in MODELS.items() for m in models] + ["Other model…"]
            pick = st.selectbox("Replies are written by", names, key="draft_model")  # Which LLM drafts replies
            if pick == "Other model…":
                provider = st.selectbox("Provider", list(MODELS), key="custom_provider")
                model = st.text_input("Model name", key="custom_name")
                c1, c2 = st.columns(2)
                p_in = c1.number_input("$ / 1M in", 0.0, value=1.0, key="custom_in")
                p_out = c2.number_input("$ / 1M out", 0.0, value=5.0, key="custom_out")
                ss.custom_model = (provider, model.strip(), p_in, p_out) if model.strip() else None
                draft = llm_spec(*ss.custom_model) if ss.custom_model else {"name": "demo"}
            else:
                provider, model = pick.split(" · ")
                draft = llm_spec(provider, model, *MODELS[provider][model])

        # Everything the triage functions need
        ss["keys"] = {"jev": ss.get("jev_key", "").strip(), **{k: draft.get(k) for k in
                      ("provider", "model", "llm_key", "price_in", "price_out", "name")}}
        k = ss["keys"]  # (ss.keys would be the session state's own keys() method)
        gmail = f"connected as {ss.gmail_login[0]} (this session only)" if ss.get("gmail_login") else "not connected"
        st.caption(f"**Gmail:** {gmail}  \n**Jev:** {'connected' if not jev_is_mock(k) else 'demo mode'}  \n"
                   f"**Replies:** {k.get('name')}{'' if not llm_is_mock(k) else ' (demo)'}")
        _settings()


def _settings() -> None:  # Session-only tweaks to config/app.yaml values
    cfg = session_config()
    with st.expander("Settings", icon=":material/tune:"):
        st.markdown("**What makes an email important?**")
        labels = {"urgency": "How urgent it is", "needs_reply": "Someone is waiting for a reply",
                  "red_flag": "It's a serious issue", "has_deadline": "It has a deadline",
                  "vip_sender": "It's from an important sender"}
        for key, label in labels.items():
            cfg["priority_weights"][key] = st.slider(label, 0.0, 1.0, float(cfg["priority_weights"][key]), 0.05, key=f"w_{key}")
        st.markdown("**What makes a good lead?**")
        for key, label in {"buying_intent": "Ready to buy", "company_fit": "Fits our customer profile",
                           "decision_maker": "Sender can decide", "budget_mentioned": "Budget mentioned",
                           "timeline": "Wants to start soon"}.items():
            cfg["lead_weights"][key] = st.slider(label, 0.0, 1.0, float(cfg["lead_weights"][key]), 0.05, key=f"lw_{key}")
        st.markdown("**When should Jev ask you?**")
        cfg["review_confidence"] = st.slider(
            "Flag for review below", 0.0, 1.0, float(cfg["review_confidence"]), 0.05, format="%.2f", key="review_conf",
            help="Higher = you check more emails. Also used as the Smart combo setting on Compare models.")
        st.markdown("**Important senders** (edit in `config/app.yaml`)")
        st.caption(", ".join(cfg["vip_senders"]))
        if st.button("Reset settings"):
            st.session_state.cfg = copy.deepcopy(config.app_config())
            for key in [k for k in st.session_state if k.startswith(("w_", "lw_")) or k == "review_conf"]:
                del st.session_state[key]
            st.rerun()


def keys() -> dict:
    """Keys from the sidebar (empty → demo mode for everything)."""
    return st.session_state.get("keys", {})


def session_config() -> dict:
    """App config plus changes made in the sidebar settings (this session only)."""
    if "cfg" not in st.session_state:
        st.session_state.cfg = copy.deepcopy(config.app_config())
    return st.session_state.cfg

