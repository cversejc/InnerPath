export const phoneIdentifierPattern = /^\d{11}$/
export const mobilePhonePattern = /^1[3-9]\d{9}$/

export function isValidMobilePhone(value) {
  return mobilePhonePattern.test(String(value ?? ''))
}
