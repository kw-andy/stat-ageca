import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Add the current directory to Python path to import app functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    format_number_fr,
    format_currency_fr,
    calculate_gap_metrics,
    fetch_data
)

class TestFormatFunctions:
    """Test French formatting functions"""

    def test_format_number_fr_zero(self):
        """Test zero values"""
        assert format_number_fr(0) == "0"
        assert format_number_fr(0.0) == "0"
        assert format_number_fr(pd.NaType()) == "0"

    def test_format_number_fr_small_numbers(self):
        """Test numbers less than 1000"""
        assert format_number_fr(1) == "1"
        assert format_number_fr(99) == "99"
        assert format_number_fr(999) == "999"

    def test_format_number_fr_thousands(self):
        """Test numbers with thousands separators"""
        assert format_number_fr(1000) == "1.000"
        assert format_number_fr(1234) == "1.234"
        assert format_number_fr(12345) == "12.345"
        assert format_number_fr(123456) == "123.456"
        assert format_number_fr(1234567) == "1.234.567"

    def test_format_number_fr_negative(self):
        """Test negative numbers"""
        assert format_number_fr(-1) == "-1"
        assert format_number_fr(-1000) == "-1.000"
        assert format_number_fr(-12345) == "-12.345"

    def test_format_currency_fr_zero(self):
        """Test zero currency values"""
        assert format_currency_fr(0) == "0 €"
        assert format_currency_fr(0.0) == "0 €"

    def test_format_currency_fr_values(self):
        """Test currency formatting"""
        assert format_currency_fr(100) == "100 €"
        assert format_currency_fr(1234) == "1.234 €"
        assert format_currency_fr(-500) == "-500 €"


class TestCalculateGapMetrics:
    """Test business metrics calculations using real-world data patterns"""

    @pytest.fixture
    def sample_reservation_data(self):
        """Sample reservation data based on CSV structure"""
        return pd.DataFrame({
            'mois': ['2023-01', '2023-02', '2023-03'],
            'nb_reservations': [10, 15, 8]
        })

    @pytest.fixture
    def sample_ca_data(self):
        """Sample CA data based on CSV structure"""
        return pd.DataFrame({
            'mois': ['2023-01', '2023-02', '2023-03'],
            'ca_brut': [12320, 18450, 9680],
            'ca_net': [12320, 18450, 9680],
            'ecart': [0, 0, 0]
        })

    @pytest.fixture
    def sample_ca_with_cancellations(self):
        """CA data with cancellations (avoir)"""
        return pd.DataFrame({
            'mois': ['2023-01', '2023-02', '2023-03'],
            'ca_brut': [12320, 18450, 9680],
            'ca_net': [11000, 16200, 8500],  # After cancellations
            'ecart': [1320, 2250, 1180]  # Avoir amounts
        })

    def test_empty_dataframes(self):
        """Test with empty dataframes"""
        empty_df = pd.DataFrame()
        result = calculate_gap_metrics(empty_df, empty_df)
        assert result == {}

    def test_basic_metrics_calculation(self, sample_reservation_data, sample_ca_data):
        """Test basic metric calculations"""
        metrics = calculate_gap_metrics(sample_reservation_data, sample_ca_data)

        # CA per reservation average
        total_resa = 10 + 15 + 8  # 33
        total_ca = 12320 + 18450 + 9680  # 40450
        expected_ca_per_resa = total_ca / total_resa

        assert abs(metrics["ca_per_resa_avg"] - expected_ca_per_resa) < 0.01
        assert "correlation" in metrics
        assert -1 <= metrics["correlation"] <= 1

    def test_correlation_calculation(self):
        """Test correlation calculation with known values"""
        # Perfect positive correlation
        resa_data = pd.DataFrame({
            'mois': ['2023-01', '2023-02', '2023-03'],
            'nb_reservations': [10, 20, 30]
        })
        ca_data = pd.DataFrame({
            'mois': ['2023-01', '2023-02', '2023-03'],
            'ca_brut': [1000, 2000, 3000],
            'ca_net': [1000, 2000, 3000],
            'ecart': [0, 0, 0]
        })

        metrics = calculate_gap_metrics(resa_data, ca_data)
        assert abs(metrics["correlation"] - 1.0) < 0.01  # Should be close to 1.0

    def test_single_data_point(self):
        """Test with single data point"""
        single_resa = pd.DataFrame({
            'mois': ['2023-01'],
            'nb_reservations': [5]
        })
        single_ca = pd.DataFrame({
            'mois': ['2023-01'],
            'ca_brut': [1000],
            'ca_net': [1000],
            'ecart': [0]
        })

        metrics = calculate_gap_metrics(single_resa, single_ca)
        assert metrics["ca_per_resa_avg"] == 200  # 1000 / 5
        assert metrics["correlation"] == 0  # Can't calculate correlation with 1 point

    def test_zero_reservations_handling(self):
        """Test handling of zero reservations (division by zero protection)"""
        zero_resa = pd.DataFrame({
            'mois': ['2023-01', '2023-02'],
            'nb_reservations': [0, 10]
        })
        ca_data = pd.DataFrame({
            'mois': ['2023-01', '2023-02'],
            'ca_brut': [0, 1000],
            'ca_net': [0, 1000],
            'ecart': [0, 0]
        })

        metrics = calculate_gap_metrics(zero_resa, ca_data)
        # Should handle division by zero gracefully
        assert metrics["ca_per_resa_avg"] == 100  # 1000 / 10 (only non-zero)

    def test_trend_analysis_sufficient_data(self):
        """Test trend analysis with sufficient data points"""
        # Create 6+ months of data
        months = ['2023-01', '2023-02', '2023-03', '2023-04', '2023-05', '2023-06']
        resa_data = pd.DataFrame({
            'mois': months,
            'nb_reservations': [10, 12, 14, 16, 18, 20]  # Growing trend
        })
        ca_data = pd.DataFrame({
            'mois': months,
            'ca_brut': [1000, 1100, 1200, 1300, 1400, 1500],  # Growing trend
            'ca_net': [1000, 1100, 1200, 1300, 1400, 1500],
            'ecart': [0, 0, 0, 0, 0, 0]
        })

        metrics = calculate_gap_metrics(resa_data, ca_data)

        # Should have growth metrics
        assert "resa_growth" in metrics
        assert "ca_growth" in metrics
        assert "growth_gap" in metrics
        assert metrics["resa_growth"] > 0  # Positive growth
        assert metrics["ca_growth"] > 0  # Positive growth

    def test_ca_per_resa_trend(self, sample_reservation_data, sample_ca_data):
        """Test CA per reservation trend calculation"""
        metrics = calculate_gap_metrics(sample_reservation_data, sample_ca_data)
        assert "ca_per_resa_trend" in metrics
        # Should be a percentage change


class TestRealWorldDataScenarios:
    """Test with patterns similar to the CSV data"""

    def test_assisteal_formation_scenario(self):
        """Test scenario similar to ASSISTEAL FORMATION data"""
        # Based on CSV: Grande salle 9, 1232€ TTC
        resa_data = pd.DataFrame({
            'mois': ['2023-01'],
            'nb_reservations': [1]
        })
        ca_data = pd.DataFrame({
            'mois': ['2023-01'],
            'ca_brut': [1232],
            'ca_net': [1232],
            'ecart': [0]
        })

        metrics = calculate_gap_metrics(resa_data, ca_data)
        assert metrics["ca_per_resa_avg"] == 1232

    def test_cfa_isw_scenario(self):
        """Test scenario similar to CFA ISW EDUCATION data"""
        # Based on CSV: Multiple small rooms, 211€ each
        resa_data = pd.DataFrame({
            'mois': ['2023-01'],
            'nb_reservations': [4]  # Multiple room reservations
        })
        ca_data = pd.DataFrame({
            'mois': ['2023-01'],
            'ca_brut': [844],  # 4 * 211
            'ca_net': [844],
            'ecart': [0]
        })

        metrics = calculate_gap_metrics(resa_data, ca_data)
        assert metrics["ca_per_resa_avg"] == 211

    def test_mixed_document_types(self):
        """Test with mixed document types (Devis vs Facture)"""
        # Some reservations might be "Devis" (quotes) vs "Facture" (invoices)
        resa_data = pd.DataFrame({
            'mois': ['2023-01', '2023-02'],
            'nb_reservations': [5, 5]
        })
        # Different CA based on document status
        ca_data = pd.DataFrame({
            'mois': ['2023-01', '2023-02'],
            'ca_brut': [1000, 1000],
            'ca_net': [800, 1000],  # Jan has some quotes that aren't invoiced yet
            'ecart': [200, 0]
        })

        metrics = calculate_gap_metrics(resa_data, ca_data)
        assert metrics["ca_per_resa_avg"] == 180  # (800 + 1000) / 10


class TestFetchDataFunction:
    """Test the SQL query generation and data fetching function"""

    @patch('app.fetch_dataframe')
    def test_fetch_data_no_filters(self, mock_fetch):
        """Test fetch_data with no filters"""
        # Mock successful database responses
        mock_fetch.side_effect = [
            pd.DataFrame({'mois': ['2023-01'], 'nb_reservations': [10]}),
            pd.DataFrame({'mois': ['2023-01'], 'ca_brut': [1000], 'ca_net': [1000]})
        ]

        df_resa, df_ca, error = fetch_data(None, None, None, "")

        assert error is None
        assert len(df_resa) == 1
        assert len(df_ca) == 1
        assert 'ecart' in df_ca.columns

    @patch('app.fetch_dataframe')
    def test_fetch_data_with_filters(self, mock_fetch):
        """Test fetch_data with various filters"""
        mock_fetch.side_effect = [
            pd.DataFrame({'mois': ['2023-01'], 'nb_reservations': [5]}),
            pd.DataFrame({'mois': ['2023-01'], 'ca_brut': [500], 'ca_net': [500]})
        ]

        df_resa, df_ca, error = fetch_data(
            date_debut="2023-01-01",
            date_fin="2023-02-01",
            statut_sel=["Encaissée"],
            organisateur="ASSISTEAL"
        )

        assert error is None
        # Verify the function was called with parameters
        assert mock_fetch.call_count == 2

    @patch('app.fetch_dataframe')
    def test_fetch_data_database_error(self, mock_fetch):
        """Test fetch_data when database query fails"""
        mock_fetch.side_effect = Exception("Database connection failed")

        df_resa, df_ca, error = fetch_data(None, None, None, "")

        assert error == "Database connection failed"
        assert df_resa.empty
        assert df_ca.empty


# Test fixture for pytest
@pytest.fixture
def real_csv_sample():
    """Load a small sample of the real CSV data for integration testing"""
    try:
        df = pd.read_csv('Liste_Option_Facturable.csv', sep=';', nrows=100, encoding='utf-8')
        return df
    except:
        # Fallback if CSV can't be read
        return pd.DataFrame()


class TestIntegrationWithRealData:
    """Integration tests using actual CSV data"""

    def test_with_real_csv_data(self, real_csv_sample):
        """Test calculations with real CSV data if available"""
        if real_csv_sample.empty:
            pytest.skip("CSV data not available")

        # Convert real data to the format expected by our functions
        # This would require mapping CSV columns to our expected format
        # For now, just test that we can process the data structure

        assert len(real_csv_sample.columns) == 20  # Expected number of columns
        assert "Prix TTC" in real_csv_sample.columns
        assert "Date de réservation" in real_csv_sample.columns


if __name__ == "__main__":
    # Run specific test groups
    pytest.main(["-v", __file__])