"""
Streamlit ダッシュボード
"""
import streamlit as st

# ページ設定
st.set_page_config(
    page_title="競馬予想AIシステム",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# タイトル
st.title("🏇 競馬予想AIシステム")
st.markdown("JRA-VAN DataLabのデータを活用した競馬予測システム")

# サイドバー
st.sidebar.title("メニュー")
st.sidebar.markdown("### 機能選択")

# メインコンテンツ
col1, col2, col3 = st.columns(3)

with col1:
    st.info("📊 データインポート")
    st.markdown("CSVファイルからデータをインポート")

with col2:
    st.success("🤖 予測実行")
    st.markdown("機械学習モデルによる予測")

with col3:
    st.warning("📈 結果分析")
    st.markdown("予測結果の分析と可視化")

# 開発中メッセージ
st.markdown("---")
st.info("🚧 システムは現在開発中です")