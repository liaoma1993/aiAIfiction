import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { useAuthStore } from '@/stores/useAuthStore';

const { Title } = Typography;

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const loginFn = useAuthStore((s) => s.login);
  const registerFn = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    try {
      if (isRegister) {
        await registerFn(values.email, values.username, values.password);
      } else {
        await loginFn(values.email, values.password);
      }
      message.success(isRegister ? '注册成功' : '登录成功');
      navigate('/dashboard');
    } catch {
      message.error(isRegister ? '注册失败' : '登录失败');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <Card style={{ width: 400, borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-md)' }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>
          {isRegister ? '注册 AI Fiction Studio' : '登录 AI Fiction Studio'}
        </Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input placeholder="邮箱" size="large" />
          </Form.Item>
          {isRegister && (
            <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input placeholder="用户名" size="large" />
            </Form.Item>
          )}
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="密码" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" style={{ height: 44 }}>
            {isRegister ? '注册' : '登录'}
          </Button>
        </Form>
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button type="link" onClick={() => setIsRegister(!isRegister)}>
            {isRegister ? '已有账号？去登录' : '没有账号？去注册'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
