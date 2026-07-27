// The English values are the contract with the API, which ships them verbatim.

export const PERSON_TYPES = ["Natural person", "Legal entity"] as const;
export type PersonType = (typeof PERSON_TYPES)[number];

export const DOCUMENT_TYPES = [
  "Citizen ID",
  "Foreigner ID",
  "NIT",
  "Minor ID",
  "Passport",
  "Birth certificate",
  "NUIP",
] as const;
export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export const GENDERS = ["Male", "Female"] as const;
export type Gender = (typeof GENDERS)[number];

export const MARITAL_STATUSES = [
  "Single",
  "Married",
  "Domestic partnership",
  "Female head of household",
  "Other",
] as const;
export type MaritalStatus = (typeof MARITAL_STATUSES)[number];

export const HOUSING_TYPES = [
  "Owned",
  "Rented",
  "Family owned",
  "Other",
] as const;
export type HousingType = (typeof HOUSING_TYPES)[number];

export const EDUCATION_LEVELS = [
  "Primary",
  "Secondary",
  "Technical",
  "University",
  "Postgraduate",
] as const;
export type EducationLevel = (typeof EDUCATION_LEVELS)[number];

export const TAX_REGIMES = [
  "Not VAT responsible",
  "VAT responsible",
  "Simplified",
  "Subsidized",
] as const;
export type TaxRegime = (typeof TAX_REGIMES)[number];

export const COMPANY_TYPES = [
  "Corporation",
  "Limited liability company",
  "Simplified joint-stock company",
  "Limited partnership by shares",
  "De facto partnership",
  "Sole proprietorship",
  "Cooperative",
  "Nonprofit organization",
  "Foundation",
  "Trade association",
  "Consortium",
  "Temporary joint venture",
] as const;
export type CompanyType = (typeof COMPANY_TYPES)[number];

export const DOCUMENT_WITH_CHECK_DIGIT: DocumentType = "NIT";

export interface Country {
  id: number;
  iso_code: string;
  name: string;
}

export interface Department {
  id: number;
  country_id: number;
  dane_code: string;
  name: string;
}

export interface City {
  id: number;
  department_id: number;
  dane_code: string;
  name: string;
}

export interface ThirdParty {
  id: number;
  person_type: PersonType;
  document_type: DocumentType;
  document_number: string;
  check_digit: number | null;
  formatted_document: string;
  full_name: string;

  first_name: string | null;
  middle_name: string | null;
  first_surname: string | null;
  second_surname: string | null;
  issue_date: string | null;
  issue_city_id: number | null;
  birth_date: string | null;
  birth_country_id: number | null;
  birth_department_id: number | null;
  birth_city_id: number | null;
  gender: Gender | null;
  marital_status: MaritalStatus | null;
  housing_type: HousingType | null;
  education_level: EducationLevel | null;
  profession: string | null;

  legal_name: string | null;
  company_type: CompanyType | null;
  company_nature: string | null;
  legal_rep_document_type: DocumentType | null;
  legal_rep_document_number: string | null;
  legal_rep_name: string | null;

  trade_name: string | null;
  address: string | null;
  country_id: number | null;
  department_id: number | null;
  city_id: number | null;
  mobile_phone: string | null;
  landline: string | null;
  email: string | null;
  tax_regime: TaxRegime;

  foreign_operations: boolean;
  public_resources: boolean;
  public_recognition: boolean;
  public_power: boolean;

  is_active: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ContactFields {
  address: string;
  country_id: number;
  department_id?: number | null;
  city_id?: number | null;
  mobile_phone: string;
  landline?: string | null;
  email: string;
  tax_regime: TaxRegime;
  trade_name?: string | null;
  foreign_operations?: boolean;
  public_resources?: boolean;
  public_recognition?: boolean;
  public_power?: boolean;
  is_active?: boolean;
}

export interface NaturalPersonCreate extends ContactFields {
  person_type: "Natural person";
  document_type: DocumentType;
  document_number: string;
  check_digit?: number | null;
  first_name: string;
  middle_name?: string | null;
  first_surname: string;
  second_surname?: string | null;
  issue_date: string;
  issue_city_id: number;
  birth_date: string;
  birth_country_id: number;
  birth_department_id?: number | null;
  birth_city_id?: number | null;
  gender: Gender;
  marital_status: MaritalStatus;
  housing_type: HousingType;
  education_level: EducationLevel;
  profession: string;
}

export interface LegalEntityCreate extends ContactFields {
  person_type: "Legal entity";
  document_number: string;
  check_digit?: number | null;
  legal_name: string;
  company_type: CompanyType;
  company_nature: string;
  legal_rep_document_type: DocumentType;
  legal_rep_document_number: string;
  legal_rep_name: string;
}

export type ThirdPartyCreate = NaturalPersonCreate | LegalEntityCreate;

export type ThirdPartyUpdate = Partial<
  Omit<ThirdPartyCreate, "person_type"> & { document_type: DocumentType }
>;

export interface ThirdPartyListParams {
  person_type?: PersonType;
  document_type?: DocumentType;
  search?: string;
  only_active?: boolean;
  include_deleted?: boolean;
  skip?: number;
  limit?: number;
}
