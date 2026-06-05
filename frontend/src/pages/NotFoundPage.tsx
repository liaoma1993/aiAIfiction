import { Button, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div style={{ textAlign: 'center', padding: 100 }}>
      <Title level={1}>404</Title>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>页面不存在</p>
      <Button type="primary" onClick={() => navigate('/dashboard')}>返回首页</Button>
    </div>
  );
}
