import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Grid, 
  CircularProgress, 
  LinearProgress, 
  Button, 
  Chip, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar
} from '@mui/material';
import { 
  Speed as SpeedIcon, 
  DataUsage as DataUsageIcon, 
  AttachMoney as MoneyIcon, 
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  History as HistoryIcon
} from '@mui/icons-material';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { formatBytes, formatDate, formatCurrency } from '../../utils/formatters';
import { tariffService } from '../../services/tariffService';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const TariffDashboard = ({ userId }) => {
  const [userPlan, setUserPlan] = useState(null);
  const [usageHistory, setUsageHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [availablePlans, setAvailablePlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch user's current tariff plan
        const planResponse = await tariffService.getUserTariffPlan(userId);
        setUserPlan(planResponse);
        
        // Fetch usage history
        const historyResponse = await tariffService.getUserUsageHistory(userId);
        setUsageHistory(historyResponse);
        
        setLoading(false);
      } catch (err) {
        setError(err.message || 'Failed to load tariff data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, [userId]);

  const handleOpenPlanDialog = async () => {
    try {
      const plans = await tariffService.getAllTariffPlans();
      setAvailablePlans(plans);
      setOpenDialog(true);
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Failed to load available plans',
        severity: 'error'
      });
    }
  };

  const handleChangePlan = async () => {
    if (!selectedPlan) return;
    
    try {
      await tariffService.changeTariffPlan(userId, selectedPlan.id);
      setOpenDialog(false);
      
      // Refresh user plan data
      const planResponse = await tariffService.getUserTariffPlan(userId);
      setUserPlan(planResponse);
      
      setSnackbar({
        open: true,
        message: 'Plan changed successfully',
        severity: 'success'
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: err.message || 'Failed to change plan',
        severity: 'error'
      });
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        {error}
      </Alert>
    );
  }

  if (!userPlan) {
    return (
      <Alert severity="info">
        No active tariff plan found. Please contact support to activate a plan.
      </Alert>
    );
  }

  // Calculate days remaining in current billing cycle
  const currentDate = new Date();
  const cycleEndDate = new Date(userPlan.current_cycle_end);
  const daysRemaining = Math.ceil((cycleEndDate - currentDate) / (1000 * 60 * 60 * 24));
  
  // Prepare data for usage chart
  const chartData = usageHistory.map(record => ({
    date: formatDate(record.timestamp),
    usage: record.total_bytes / (1024 * 1024 * 1024), // Convert to GB
  }));
  
  // Prepare data for usage breakdown pie chart
  const pieData = [
    { name: 'Used', value: userPlan.data_used },
    { name: 'Remaining', value: userPlan.data_cap - userPlan.data_used }
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Tariff Dashboard
      </Typography>
      
      {/* Plan Summary Card */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="h5">{userPlan.plan_name}</Typography>
              <Typography variant="body1" color="textSecondary">
                {userPlan.plan_description}
              </Typography>
              
              <Box mt={2} display="flex" alignItems="center">
                <MoneyIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">
                  {formatCurrency(userPlan.price)} / {userPlan.billing_cycle}
                </Typography>
              </Box>
              
              <Box mt={1} display="flex" alignItems="center">
                <SpeedIcon color="primary" sx={{ mr: 1 }} />
                <Typography>
                  {userPlan.download_speed} Mbps ↓ / {userPlan.upload_speed} Mbps ↑
                </Typography>
              </Box>
              
              <Box mt={2}>
                <Chip 
                  label={userPlan.status.toUpperCase()} 
                  color={userPlan.status === 'active' ? 'success' : 'warning'}
                  icon={userPlan.status === 'active' ? <CheckCircleIcon /> : <WarningIcon />}
                />
                
                {userPlan.is_throttled && (
                  <Chip 
                    label="THROTTLED" 
                    color="error"
                    icon={<WarningIcon />}
                    sx={{ ml: 1 }}
                  />
                )}
              </Box>
              
              <Box mt={2}>
                <Button 
                  variant="contained" 
                  color="primary"
                  onClick={handleOpenPlanDialog}
                >
                  Change Plan
                </Button>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box mb={2}>
                <Typography variant="subtitle1">
                  Data Usage: {formatBytes(userPlan.data_used)} of {formatBytes(userPlan.data_cap)}
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={userPlan.percentage_used} 
                  color={userPlan.percentage_used > 90 ? "error" : userPlan.percentage_used > 75 ? "warning" : "primary"}
                  sx={{ height: 10, borderRadius: 5 }}
                />
              </Box>
              
              <Box display="flex" justifyContent="space-between" mt={3}>
                <Box textAlign="center">
                  <Typography variant="h6">{daysRemaining}</Typography>
                  <Typography variant="body2" color="textSecondary">Days Remaining</Typography>
                </Box>
                
                <Box textAlign="center">
                  <Typography variant="h6">{formatDate(userPlan.current_cycle_start)}</Typography>
                  <Typography variant="body2" color="textSecondary">Cycle Start</Typography>
                </Box>
                
                <Box textAlign="center">
                  <Typography variant="h6">{formatDate(userPlan.current_cycle_end)}</Typography>
                  <Typography variant="body2" color="textSecondary">Cycle End</Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Usage Charts */}
      <Grid container spacing={4}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <DataUsageIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Usage History
              </Typography>
              
              <Box height={300}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={chartData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis label={{ value: 'GB', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(value) => [`${value.toFixed(2)} GB`, 'Usage']} />
                    <Area type="monotone" dataKey="usage" stroke="#8884d8" fill="#8884d8" />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <DataUsageIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Usage Breakdown
              </Typography>
              
              <Box height={250} display="flex" justifyContent="center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatBytes(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
              
              <Box mt={2} textAlign="center">
                <Typography variant="body2" color="textSecondary">
                  {userPlan.data_cap ? (
                    `${formatBytes(userPlan.data_cap - userPlan.data_used)} remaining`
                  ) : (
                    'Unlimited data plan'
                  )}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Recent Usage Records */}
      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            <HistoryIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
            Recent Usage Records
          </Typography>
          
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Download</TableCell>
                  <TableCell>Upload</TableCell>
                  <TableCell>Total</TableCell>
                  <TableCell>Source</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usageHistory.slice(0, 5).map((record) => (
                  <TableRow key={record.id}>
                    <TableCell>{formatDate(record.timestamp)}</TableCell>
                    <TableCell>{formatBytes(record.download_bytes)}</TableCell>
                    <TableCell>{formatBytes(record.upload_bytes)}</TableCell>
                    <TableCell>{formatBytes(record.total_bytes)}</TableCell>
                    <TableCell>{record.source}</TableCell>
                  </TableRow>
                ))}
                {usageHistory.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">No usage records found</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      
      {/* Change Plan Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Change Tariff Plan</DialogTitle>
        <DialogContent>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell></TableCell>
                  <TableCell>Plan</TableCell>
                  <TableCell>Speed</TableCell>
                  <TableCell>Data Cap</TableCell>
                  <TableCell>Price</TableCell>
                  <TableCell>Features</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {availablePlans.map((plan) => (
                  <TableRow 
                    key={plan.id}
                    selected={selectedPlan?.id === plan.id}
                    onClick={() => setSelectedPlan(plan)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      {plan.id === userPlan.plan_id && (
                        <Chip size="small" label="Current" color="primary" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="subtitle2">{plan.name}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        {plan.description}
                      </Typography>
                    </TableCell>
                    <TableCell>{plan.download_speed} / {plan.upload_speed} Mbps</TableCell>
                    <TableCell>{plan.data_cap ? formatBytes(plan.data_cap) : 'Unlimited'}</TableCell>
                    <TableCell>{formatCurrency(plan.price)}</TableCell>
                    <TableCell>
                      {plan.features && Object.entries(plan.features).map(([key, value]) => (
                        value && (
                          <Chip 
                            key={key} 
                            label={key.replace('_', ' ')} 
                            size="small" 
                            sx={{ mr: 0.5, mb: 0.5 }} 
                          />
                        )
                      ))}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          {selectedPlan && selectedPlan.id !== userPlan.plan_id && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {selectedPlan.price > userPlan.price ? (
                <>
                  This is an upgrade. You will be charged a prorated amount for the remainder of your billing cycle.
                </>
              ) : (
                <>
                  This is a downgrade. You may receive a prorated credit for the remainder of your billing cycle.
                </>
              )}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleChangePlan} 
            variant="contained" 
            color="primary"
            disabled={!selectedPlan || selectedPlan.id === userPlan.plan_id}
          >
            Confirm Change
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TariffDashboard;
