export interface Account {
  id: string;

  application: string;

  username: string;

  firstName: string;

  lastName: string;

  email: string;

  employeeId?: string;

  department?: string;
}