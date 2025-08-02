"""データ品質レポート機能

欠損値統計、データ分布可視化、異常値レポートを生成する
"""

from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
from pathlib import Path
from loguru import logger

from src.core.exceptions import DataProcessingError


class DataQualityReporter:
    """データ品質レポートを生成するクラス"""
    
    def __init__(self, output_dir: str = "outputs/reports"):
        """初期化
        
        Args:
            output_dir: レポート出力ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 日本語フォント設定
        plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
        plt.rcParams['axes.unicode_minus'] = False
        
    def generate_missing_value_report(
        self,
        df: pd.DataFrame,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """欠損値統計レポートの生成
        
        Args:
            df: 分析対象のデータフレーム
            output_file: 出力ファイル名（Noneの場合は自動生成）
            
        Returns:
            欠損値統計の辞書
        """
        logger.info("欠損値統計レポート生成開始")
        
        try:
            # 欠損値の集計
            missing_stats = []
            
            for col in df.columns:
                missing_count = df[col].isnull().sum()
                missing_ratio = missing_count / len(df)
                
                stats = {
                    'column': col,
                    'dtype': str(df[col].dtype),
                    'missing_count': int(missing_count),
                    'missing_ratio': float(missing_ratio),
                    'missing_percentage': float(missing_ratio * 100),
                    'non_missing_count': int(len(df) - missing_count),
                    'unique_values': int(df[col].nunique()),
                    'has_missing': bool(missing_count > 0)
                }
                
                missing_stats.append(stats)
            
            # データフレームに変換
            missing_df = pd.DataFrame(missing_stats)
            missing_df = missing_df.sort_values('missing_ratio', ascending=False)
            
            # サマリー統計
            summary = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns_with_missing': int((missing_df['missing_count'] > 0).sum()),
                'columns_without_missing': int((missing_df['missing_count'] == 0).sum()),
                'total_missing_values': int(missing_df['missing_count'].sum()),
                'average_missing_ratio': float(missing_df['missing_ratio'].mean()),
                'max_missing_ratio': float(missing_df['missing_ratio'].max()),
                'columns_over_50pct_missing': int((missing_df['missing_ratio'] > 0.5).sum()),
                'columns_over_80pct_missing': int((missing_df['missing_ratio'] > 0.8).sum())
            }
            
            # 欠損値パターンの分析
            missing_patterns = self._analyze_missing_patterns(df)
            
            # レポート全体
            report = {
                'generated_at': datetime.now().isoformat(),
                'summary': summary,
                'column_statistics': missing_df.to_dict('records'),
                'missing_patterns': missing_patterns,
                'recommendations': self._generate_missing_value_recommendations(missing_df)
            }
            
            # ファイル出力
            if output_file is None:
                output_file = f"missing_value_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"欠損値統計レポート生成完了: {output_path}")
            
            # 可視化
            self._visualize_missing_values(missing_df, output_file.replace('.json', '.png'))
            
            return report
            
        except Exception as e:
            raise DataProcessingError(f"欠損値統計レポート生成中にエラーが発生しました: {str(e)}")
    
    def _analyze_missing_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """欠損値パターンの分析
        
        Args:
            df: データフレーム
            
        Returns:
            欠損値パターンの分析結果
        """
        # 行ごとの欠損値数
        missing_per_row = df.isnull().sum(axis=1)
        
        # パターン統計
        patterns = {
            'rows_with_no_missing': int((missing_per_row == 0).sum()),
            'rows_with_any_missing': int((missing_per_row > 0).sum()),
            'rows_with_all_missing': int((missing_per_row == len(df.columns)).sum()),
            'average_missing_per_row': float(missing_per_row.mean()),
            'max_missing_per_row': int(missing_per_row.max()),
            'missing_per_row_distribution': {
                '0': int((missing_per_row == 0).sum()),
                '1-5': int(((missing_per_row >= 1) & (missing_per_row <= 5)).sum()),
                '6-10': int(((missing_per_row >= 6) & (missing_per_row <= 10)).sum()),
                '11-20': int(((missing_per_row >= 11) & (missing_per_row <= 20)).sum()),
                '>20': int((missing_per_row > 20).sum())
            }
        }
        
        # 欠損値の相関（どのカラムが同時に欠損しやすいか）
        missing_corr = df.isnull().astype(int).corr()
        high_corr_pairs = []
        
        for i in range(len(missing_corr.columns)):
            for j in range(i + 1, len(missing_corr.columns)):
                corr_value = missing_corr.iloc[i, j]
                if abs(corr_value) > 0.5:  # 相関係数0.5以上
                    high_corr_pairs.append({
                        'column1': missing_corr.columns[i],
                        'column2': missing_corr.columns[j],
                        'correlation': float(corr_value)
                    })
        
        patterns['highly_correlated_missing'] = high_corr_pairs
        
        return patterns
    
    def _generate_missing_value_recommendations(self, missing_df: pd.DataFrame) -> List[str]:
        """欠損値処理の推奨事項を生成
        
        Args:
            missing_df: 欠損値統計データフレーム
            
        Returns:
            推奨事項のリスト
        """
        recommendations = []
        
        # 欠損率が高いカラムへの対処
        high_missing = missing_df[missing_df['missing_ratio'] > 0.8]
        if len(high_missing) > 0:
            cols = high_missing['column'].tolist()
            recommendations.append(
                f"以下のカラムは欠損率が80%を超えています。削除を検討してください: {', '.join(cols)}"
            )
        
        # 欠損率が中程度のカラムへの対処
        medium_missing = missing_df[(missing_df['missing_ratio'] > 0.2) & (missing_df['missing_ratio'] <= 0.8)]
        if len(medium_missing) > 0:
            recommendations.append(
                f"{len(medium_missing)}個のカラムで欠損率が20-80%です。補完方法を慎重に選択してください。"
            )
        
        # データ型別の推奨
        numeric_missing = missing_df[
            (missing_df['dtype'].str.contains('int|float')) & 
            (missing_df['missing_count'] > 0)
        ]
        if len(numeric_missing) > 0:
            recommendations.append(
                "数値型カラムの欠損値には、平均値、中央値、または予測モデルによる補完を検討してください。"
            )
        
        categorical_missing = missing_df[
            (missing_df['dtype'] == 'object') & 
            (missing_df['missing_count'] > 0)
        ]
        if len(categorical_missing) > 0:
            recommendations.append(
                "カテゴリ型カラムの欠損値には、最頻値または'不明'カテゴリでの補完を検討してください。"
            )
        
        return recommendations
    
    def _visualize_missing_values(self, missing_df: pd.DataFrame, output_file: str):
        """欠損値の可視化
        
        Args:
            missing_df: 欠損値統計データフレーム
            output_file: 出力ファイル名
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('欠損値分析レポート', fontsize=16)
        
        # 1. 欠損率の棒グラフ（上位20カラム）
        ax1 = axes[0, 0]
        top_missing = missing_df.head(20)
        ax1.barh(top_missing['column'], top_missing['missing_percentage'])
        ax1.set_xlabel('欠損率 (%)')
        ax1.set_title('欠損率上位20カラム')
        ax1.invert_yaxis()
        
        # 2. 欠損値の有無の円グラフ
        ax2 = axes[0, 1]
        missing_counts = [
            len(missing_df[missing_df['missing_count'] == 0]),
            len(missing_df[missing_df['missing_count'] > 0])
        ]
        ax2.pie(missing_counts, labels=['欠損なし', '欠損あり'], autopct='%1.1f%%')
        ax2.set_title('カラムの欠損値有無')
        
        # 3. 欠損率の分布
        ax3 = axes[1, 0]
        ax3.hist(missing_df[missing_df['missing_ratio'] > 0]['missing_ratio'] * 100, 
                bins=20, edgecolor='black')
        ax3.set_xlabel('欠損率 (%)')
        ax3.set_ylabel('カラム数')
        ax3.set_title('欠損率の分布（欠損があるカラムのみ）')
        
        # 4. データ型別の欠損値統計
        ax4 = axes[1, 1]
        dtype_stats = missing_df.groupby('dtype')['missing_count'].sum()
        ax4.bar(dtype_stats.index, dtype_stats.values)
        ax4.set_xlabel('データ型')
        ax4.set_ylabel('欠損値の総数')
        ax4.set_title('データ型別欠損値数')
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"欠損値可視化完了: {output_path}")
    
    def generate_distribution_report(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """データ分布レポートの生成
        
        Args:
            df: 分析対象のデータフレーム
            columns: 分析対象カラム（Noneの場合は数値カラム全て）
            output_file: 出力ファイル名
            
        Returns:
            データ分布統計の辞書
        """
        logger.info("データ分布レポート生成開始")
        
        try:
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            distribution_stats = []
            
            for col in columns:
                if col not in df.columns:
                    continue
                
                data = df[col].dropna()
                
                if len(data) == 0:
                    continue
                
                # 基本統計量
                stats = {
                    'column': col,
                    'count': int(len(data)),
                    'mean': float(data.mean()),
                    'std': float(data.std()),
                    'min': float(data.min()),
                    'q25': float(data.quantile(0.25)),
                    'median': float(data.quantile(0.50)),
                    'q75': float(data.quantile(0.75)),
                    'max': float(data.max()),
                    'skewness': float(data.skew()),
                    'kurtosis': float(data.kurtosis()),
                    'unique_count': int(data.nunique()),
                    'mode': float(data.mode().iloc[0]) if len(data.mode()) > 0 else None
                }
                
                # 分布の特徴
                stats['is_normal'] = abs(stats['skewness']) < 0.5 and abs(stats['kurtosis']) < 3
                stats['is_skewed'] = abs(stats['skewness']) > 1
                stats['has_outliers'] = self._detect_outliers_iqr(data)
                
                distribution_stats.append(stats)
            
            # レポート全体
            report = {
                'generated_at': datetime.now().isoformat(),
                'column_count': len(distribution_stats),
                'statistics': distribution_stats,
                'summary': self._generate_distribution_summary(distribution_stats)
            }
            
            # ファイル出力
            if output_file is None:
                output_file = f"distribution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"データ分布レポート生成完了: {output_path}")
            
            # 可視化
            self._visualize_distributions(df, columns[:12], output_file.replace('.json', '.png'))
            
            return report
            
        except Exception as e:
            raise DataProcessingError(f"データ分布レポート生成中にエラーが発生しました: {str(e)}")
    
    def _detect_outliers_iqr(self, data: pd.Series, threshold: float = 1.5) -> bool:
        """IQR法による外れ値の検出
        
        Args:
            data: データシリーズ
            threshold: IQR倍率の閾値
            
        Returns:
            外れ値が存在するかどうか
        """
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        outliers = (data < lower_bound) | (data > upper_bound)
        return outliers.any()
    
    def _generate_distribution_summary(self, stats: List[Dict]) -> Dict[str, Any]:
        """分布統計のサマリー生成
        
        Args:
            stats: カラム別統計情報のリスト
            
        Returns:
            サマリー情報
        """
        stats_df = pd.DataFrame(stats)
        
        summary = {
            'normal_distributed_columns': int(stats_df['is_normal'].sum()),
            'skewed_columns': int(stats_df['is_skewed'].sum()),
            'columns_with_outliers': int(stats_df['has_outliers'].sum()),
            'highly_skewed_columns': stats_df[stats_df['skewness'].abs() > 2]['column'].tolist(),
            'high_kurtosis_columns': stats_df[stats_df['kurtosis'].abs() > 7]['column'].tolist()
        }
        
        return summary
    
    def _visualize_distributions(self, df: pd.DataFrame, columns: List[str], output_file: str):
        """データ分布の可視化
        
        Args:
            df: データフレーム
            columns: 可視化対象カラム
            output_file: 出力ファイル名
        """
        n_cols = min(len(columns), 12)
        n_rows = (n_cols + 2) // 3
        
        fig, axes = plt.subplots(n_rows, 3, figsize=(15, 4 * n_rows))
        fig.suptitle('データ分布レポート', fontsize=16)
        
        axes_flat = axes.flatten() if n_rows > 1 else [axes]
        
        for i, col in enumerate(columns[:n_cols]):
            ax = axes_flat[i]
            data = df[col].dropna()
            
            # ヒストグラムとKDE
            ax.hist(data, bins=30, density=True, alpha=0.7, edgecolor='black')
            data.plot.kde(ax=ax, color='red', linewidth=2)
            
            ax.set_title(f'{col}')
            ax.set_xlabel('値')
            ax.set_ylabel('密度')
            
            # 統計情報を追加
            textstr = f'平均: {data.mean():.2f}\n標準偏差: {data.std():.2f}\n歪度: {data.skew():.2f}'
            ax.text(0.65, 0.95, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 余白の軸を非表示
        for i in range(n_cols, len(axes_flat)):
            axes_flat[i].set_visible(False)
        
        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"データ分布可視化完了: {output_path}")
    
    def generate_outlier_report(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = 'iqr',
        threshold: float = 1.5,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """異常値レポートの生成
        
        Args:
            df: 分析対象のデータフレーム
            columns: 分析対象カラム
            method: 外れ値検出方法
            threshold: 閾値
            output_file: 出力ファイル名
            
        Returns:
            異常値統計の辞書
        """
        logger.info("異常値レポート生成開始")
        
        try:
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            outlier_stats = []
            outlier_indices = set()
            
            for col in columns:
                if col not in df.columns:
                    continue
                
                data = df[col].dropna()
                
                if len(data) == 0:
                    continue
                
                # 外れ値検出
                if method == 'iqr':
                    Q1 = data.quantile(0.25)
                    Q3 = data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR
                    outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                elif method == 'zscore':
                    z_scores = np.abs((df[col] - data.mean()) / data.std())
                    outliers = z_scores > threshold
                else:
                    raise ValueError(f"不明な外れ値検出方法: {method}")
                
                outlier_count = outliers.sum()
                outlier_ratio = outlier_count / len(df)
                
                # 外れ値の詳細
                outlier_values = df.loc[outliers, col].values
                
                stats = {
                    'column': col,
                    'outlier_count': int(outlier_count),
                    'outlier_ratio': float(outlier_ratio),
                    'outlier_percentage': float(outlier_ratio * 100),
                    'method': method,
                    'threshold': threshold
                }
                
                if method == 'iqr':
                    stats['lower_bound'] = float(lower_bound)
                    stats['upper_bound'] = float(upper_bound)
                    stats['iqr'] = float(IQR)
                
                if len(outlier_values) > 0:
                    stats['outlier_min'] = float(outlier_values.min())
                    stats['outlier_max'] = float(outlier_values.max())
                    stats['outlier_mean'] = float(outlier_values.mean())
                    
                    # 外れ値のサンプル（最大10個）
                    sample_size = min(10, len(outlier_values))
                    stats['outlier_samples'] = outlier_values[:sample_size].tolist()
                
                outlier_stats.append(stats)
                
                # 外れ値を持つ行のインデックスを記録
                outlier_indices.update(df[outliers].index.tolist())
            
            # レポート全体
            report = {
                'generated_at': datetime.now().isoformat(),
                'method': method,
                'threshold': threshold,
                'total_rows': len(df),
                'rows_with_outliers': len(outlier_indices),
                'rows_with_outliers_ratio': len(outlier_indices) / len(df),
                'column_statistics': outlier_stats,
                'summary': self._generate_outlier_summary(outlier_stats),
                'recommendations': self._generate_outlier_recommendations(outlier_stats)
            }
            
            # ファイル出力
            if output_file is None:
                output_file = f"outlier_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"異常値レポート生成完了: {output_path}")
            
            # 可視化
            self._visualize_outliers(df, outlier_stats[:9], output_file.replace('.json', '.png'))
            
            return report
            
        except Exception as e:
            raise DataProcessingError(f"異常値レポート生成中にエラーが発生しました: {str(e)}")
    
    def _generate_outlier_summary(self, stats: List[Dict]) -> Dict[str, Any]:
        """外れ値統計のサマリー生成
        
        Args:
            stats: カラム別外れ値統計のリスト
            
        Returns:
            サマリー情報
        """
        stats_df = pd.DataFrame(stats)
        
        summary = {
            'columns_with_outliers': int((stats_df['outlier_count'] > 0).sum()),
            'total_outliers': int(stats_df['outlier_count'].sum()),
            'average_outlier_ratio': float(stats_df['outlier_ratio'].mean()),
            'max_outlier_ratio': float(stats_df['outlier_ratio'].max()),
            'columns_over_5pct_outliers': stats_df[stats_df['outlier_ratio'] > 0.05]['column'].tolist(),
            'columns_over_10pct_outliers': stats_df[stats_df['outlier_ratio'] > 0.10]['column'].tolist()
        }
        
        return summary
    
    def _generate_outlier_recommendations(self, stats: List[Dict]) -> List[str]:
        """外れ値処理の推奨事項を生成
        
        Args:
            stats: カラム別外れ値統計のリスト
            
        Returns:
            推奨事項のリスト
        """
        recommendations = []
        stats_df = pd.DataFrame(stats)
        
        # 外れ値が多いカラム
        high_outlier = stats_df[stats_df['outlier_ratio'] > 0.10]
        if len(high_outlier) > 0:
            cols = high_outlier['column'].tolist()
            recommendations.append(
                f"以下のカラムは外れ値率が10%を超えています: {', '.join(cols)}。"
                "データの収集プロセスを確認するか、ロバストな手法の使用を検討してください。"
            )
        
        # 外れ値が少ないカラム
        low_outlier = stats_df[(stats_df['outlier_ratio'] > 0) & (stats_df['outlier_ratio'] <= 0.05)]
        if len(low_outlier) > 0:
            recommendations.append(
                f"{len(low_outlier)}個のカラムで外れ値率が5%以下です。"
                "これらは個別に確認して適切に処理することを推奨します。"
            )
        
        # 処理方法の提案
        if len(stats_df[stats_df['outlier_count'] > 0]) > 0:
            recommendations.append(
                "外れ値の処理方法として、以下を検討してください:\n"
                "1. Winsorization（上下限でクリッピング）\n"
                "2. 対数変換やBox-Cox変換\n"
                "3. ロバスト統計量の使用\n"
                "4. 外れ値を別カテゴリとして扱う"
            )
        
        return recommendations
    
    def _visualize_outliers(self, df: pd.DataFrame, stats: List[Dict], output_file: str):
        """外れ値の可視化
        
        Args:
            df: データフレーム
            stats: 外れ値統計のリスト
            output_file: 出力ファイル名
        """
        n_cols = min(len(stats), 9)
        n_rows = (n_cols + 2) // 3
        
        fig, axes = plt.subplots(n_rows, 3, figsize=(15, 4 * n_rows))
        fig.suptitle('異常値分析レポート', fontsize=16)
        
        axes_flat = axes.flatten() if n_rows > 1 else [axes]
        
        for i, stat in enumerate(stats[:n_cols]):
            ax = axes_flat[i]
            col = stat['column']
            
            # 箱ひげ図
            df.boxplot(column=col, ax=ax)
            
            # 外れ値情報を追加
            textstr = (f"外れ値数: {stat['outlier_count']}\n"
                      f"外れ値率: {stat['outlier_percentage']:.1f}%")
            
            if 'lower_bound' in stat:
                textstr += f"\n下限: {stat['lower_bound']:.2f}\n上限: {stat['upper_bound']:.2f}"
            
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
            
            ax.set_title(f'{col}')
            ax.set_ylabel('値')
        
        # 余白の軸を非表示
        for i in range(n_cols, len(axes_flat)):
            axes_flat[i].set_visible(False)
        
        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"異常値可視化完了: {output_path}")
    
    def generate_comprehensive_report(
        self,
        df: pd.DataFrame,
        output_prefix: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """包括的なデータ品質レポートの生成
        
        Args:
            df: 分析対象のデータフレーム
            output_prefix: 出力ファイル名のプレフィックス
            
        Returns:
            全レポートの辞書
        """
        logger.info("包括的データ品質レポート生成開始")
        
        if output_prefix is None:
            output_prefix = f"data_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            reports = {}
            
            # 欠損値レポート
            reports['missing_values'] = self.generate_missing_value_report(
                df, f"{output_prefix}_missing.json"
            )
            
            # データ分布レポート
            reports['distribution'] = self.generate_distribution_report(
                df, output_file=f"{output_prefix}_distribution.json"
            )
            
            # 異常値レポート
            reports['outliers'] = self.generate_outlier_report(
                df, output_file=f"{output_prefix}_outliers.json"
            )
            
            # 統合サマリー
            summary = {
                'generated_at': datetime.now().isoformat(),
                'dataset_shape': {'rows': len(df), 'columns': len(df.columns)},
                'missing_value_summary': reports['missing_values']['summary'],
                'distribution_summary': reports['distribution']['summary'],
                'outlier_summary': reports['outliers']['summary']
            }
            
            summary_path = self.output_dir / f"{output_prefix}_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"包括的データ品質レポート生成完了: {self.output_dir}")
            
            return reports
            
        except Exception as e:
            raise DataProcessingError(f"包括的レポート生成中にエラーが発生しました: {str(e)}")